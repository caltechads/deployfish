import json
import os
import os.path
import re
from typing import Dict, List, Any, Union, TYPE_CHECKING, cast

import boto3
import botocore
import requests

from deployfish.exceptions import NoSuchTerraformStateFile, SchemaException, ConfigProcessingFailed
from deployfish.core.aws import get_boto3_session

from .abstract import AbstractConfigProcessor

if TYPE_CHECKING:
    from deployfish.config import Config


class TerraformStateFactory:

    @staticmethod
    def new(terraform_config: Dict[str, Any], context: Dict[str, Any]) -> "AbstractTerraformState":
        if 'organization' in terraform_config:
            return TerraformEnterpriseState(terraform_config, context)
        if 'statefile' in terraform_config:
            return TerraformS3State(terraform_config, context)
        raise SchemaException(
            'Could not determine location of the Terraform statefile. Ensure that you define either '  # noqa:E113
            '"organization" and "workspace" (for Terraform Enterprise) or "statefile" (for S3 hosted '
            'Terraform state) in your "terraform:" section of deployfish.yml'
        )


class AbstractTerraformState:

    def __init__(self, terraform_config: Dict[str, Any], context: Dict[str, Any]) -> None:
        self.context: Dict[str, Any] = context
        self.terraform_config: Dict[str, Any] = terraform_config
        self.loaded: bool = False
        self.terraform_lookups: Dict[str, Dict[str, str]] = {}

    def load(self, replacements: Dict[str, str]) -> None:
        raise NotImplementedError

    def lookup(self, attr: str, replacements: Dict[str, str]) -> str:
        lookup_key = self.terraform_config['lookups'][attr]
        for key, value in list(replacements.items()):
            lookup_key = lookup_key.replace(key, value)
        return self.terraform_lookups[lookup_key]['value']


class TerraformS3State(AbstractTerraformState):

    def __init__(self, terraform_config: Dict[str, Any], context: Dict[str, Any]) -> None:
        super().__init__(terraform_config, context)
        self.replacements: Dict[str, str] = {}

    def _get_state_file_from_s3(
        self,
        state_file_url: str,
        profile: str = None,
        region: str = None
    ) -> Dict[str, Any]:
        """
        Retrive our statefile from S3
        """
        if profile:
            session = boto3.session.Session(profile_name=profile, region_name=region)
        else:
            session = get_boto3_session()
        s3 = session.resource('s3')
        parts = state_file_url[5:].split('/')
        bucket = parts[0]
        filename = "/".join(parts[1:])
        key = s3.Object(bucket, filename)
        try:
            state_file = key.get()["Body"].read().decode('utf-8')
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == 'NoSuchKey':
                raise NoSuchTerraformStateFile("Could not find Terraform state file {}".format(state_file_url))
            raise ex
        return json.loads(state_file)

    def _load_pre_version_12(self, tfstate: Dict[str, Any]) -> None:
        for i in tfstate['modules']:
            if i['path'] == ['root']:
                for key, value in list(i['outputs'].items()):
                    self.terraform_lookups[key] = value

    def _load_post_version_12(self, tfstate: Dict[str, Any]) -> None:
        for key, value in list(tfstate['outputs'].items()):
            self.terraform_lookups[key] = value

    def load(self, replacements: Dict[str, str]) -> None:
        if replacements == self.replacements:
            return
        self.replacements = replacements
        statefile_url = self.terraform_config['statefile']
        for key, value in replacements.items():
            statefile_url = statefile_url.replace(key, value)
        if not self.loaded:
            tfstate = self._get_state_file_from_s3(
                statefile_url,
                profile=self.terraform_config.get('profile', None),
                region=self.terraform_config.get('region', None)
            )
            major, minor, _ = tfstate['terraform_version'].split('.')
            if int(major) >= 1 or (int(major) == 0 and int(minor) >= 12):
                self._load_post_version_12(tfstate)
            else:
                self._load_pre_version_12(tfstate)
            # If our statefile URL has no replacments in it, we don't need to load this again
            self.loaded = not any(
                r in self.terraform_config['statefile'] for r in AbstractConfigProcessor.REPLACEMENTS
            )


class TerraformEnterpriseState(AbstractTerraformState):

    TERRAFORM_API_ENDPOINT: str = 'https://app.terraform.io/api/v2'

    def __init__(self, terraform_config: Dict[str, Any], context: Dict[str, Any]) -> None:
        super().__init__(terraform_config, context)
        if 'workspace' not in self.terraform_config:
            raise SchemaException(
                'In the "terraform:" section, if you define "organization", you must also define "workspace"'
            )
        if 'tfe_token' in self.context:
            self.api_token: str = self.context['tfe_token']
        if 'ATLAS_TOKEN' in os.environ:
            self.api_token = cast(str, os.getenv('ATLAS_TOKEN'))
        if not hasattr(self, 'tfe_token'):
            raise ConfigProcessingFailed("Terraform Enterprise State: No Terraform Enterprise API token provided!")

    def get_terraform_state_download_url(self) -> str:
        endpoint = self.TERRAFORM_API_ENDPOINT + "/state-versions?"
        org_filter = "filter[organization][name]=" + self.terraform_config['organization']
        workspace_filter = "filter[workspace][name]=" + self.terraform_config['workspace']
        web_request = endpoint + org_filter + "&" + workspace_filter
        headers = {
            'Authorization': 'Bearer ' + self.api_token,
            'Content-Type': 'application/vnd.api+json'
        }
        response = requests.get(web_request, headers=headers)
        data = json.loads(response.text)
        return data['data'][0]['attributes']['hosted-state-download-url']

    def load(self, _: Dict[str, str]) -> None:
        if not self.loaded:
            state_download_url = self.get_terraform_state_download_url()
            response = requests.get(state_download_url)
            tfstate = json.loads(response.text)
            for i in tfstate['modules']:
                if i['path'] == ['root']:
                    for key, value in list(i['outputs'].items()):
                        self.terraform_lookups[key] = value
            self.loaded = True


class TerraformStateConfigProcessor(AbstractConfigProcessor):
    """
    Process our deployfish.yml file, replacing any strings that look like
    ``${terraform.KEY}`` with the value from the ``terraform:`` section.  This
    means the key to which we assign the value from the state file.

    Example:

        If our terraform section looks like this::

            terraform:
                statefile: s3://my-statefile
                lookups:
                    cluster_name: 'prod-cluster-name'


        Then ``${terraform.cluster_name}`` will be replace by the value of the
        ``prod-cluster-name`` output from the the statefile
        ``s3://my-statefile``.

    Args:
        config: the :py:class:`deployfish.config.Config` object we're working
            with
        context: a dict of additional data that we might use when processing the
            config
    """

    #: The
    TERRAFORM_RE = re.compile(r'\$\{terraform.(?P<key>[A-Za-z0-9_]+)\}')

    def __init__(self, config: "Config", context: Dict[str, Any]) -> None:
        super().__init__(config, context)
        try:
            self.terraform = TerraformStateFactory.new(config.raw['terraform'], context)
        except KeyError:
            raise self.SkipConfigProcessing('Skipping terraform state processing: no "terraform" section')

    def replace(
        self,
        obj: Union[List, Dict],
        key: Any,
        value: str,
        section_name: str,
        item_name: str
    ) -> None:
        """
        Perform string replacements on ``value``, a string value in our
        ``deployfish.yml`` item, replacing any strings that look like
        ``${terraform.KEY}`` with the value from the ``terraform:`` section.  This
        means the key to which we assign the value from the state file.

        Example:

            If our terraform section looks like this::

                terraform:
                    statefile: s3://my-statefile
                    lookups:
                        cluster_name: 'prod-cluster-name'


            Then ``${terraform.cluster_name}`` will be replaced by the value of the
            ``prod-cluster-name`` output from the the statefile
            ``s3://my-statefile``.

        Args:
            obj: a list or dict from an item from a ``deployfish.yml``
            key: the name of the key (if ``obj`` is a dict) or index (if ``obj``
                is a list``) in ``obj``
            value: our string value from ``obj[key]``
            section_name: the section name ``obj`` came from
            item_name: the name of the item in ``section_name`` that ``obj``
                came from
        """
        m = self.TERRAFORM_RE.search(value)
        if m:
            if section_name == 'tunnels':
                replacers = self.get_deployfish_replacements('services', cast(Dict, obj)['service'])
            else:
                replacers = self.get_deployfish_replacements(section_name, item_name)
            try:
                self.terraform.load(replacers)
            except NoSuchTerraformStateFile as e:
                raise self.ProcessingFailed(str(e))
            try:
                tfvalue = self.terraform.lookup(m.group('key'), replacers)
            except KeyError:
                raise self.ProcessingFailed(
                    'Config["{}"]["{}"]: There is no terraform output named "{}" in the statefile'.format(
                        section_name,
                        item_name,
                        m.group('key')
                    )
                )
            if isinstance(tfvalue, (list, tuple, dict)):
                obj[key] = tfvalue
            elif isinstance(tfvalue, int):
                obj[key] = self.TERRAFORM_RE.sub(str(tfvalue), value)
            else:
                obj[key] = self.TERRAFORM_RE.sub(tfvalue, value)
