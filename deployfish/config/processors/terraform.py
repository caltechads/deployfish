import json
import os
import os.path
import re

import boto3
import botocore
import requests

from deployfish.exceptions import NoSuchTerraformStateFile, SchemaException
from deployfish.core.aws import get_boto3_session

from .abstract import AbstractConfigProcessor


class TerraformStateFactory(object):

    @staticmethod
    def new(terraform_config, context):
        if 'organization' in terraform_config:
            return TerraformEnterpriseState(terraform_config, context)
        elif 'statefile' in terraform_config:
            return TerraformS3State(terraform_config, context)
        else:
            raise SchemaException(
                'Could not determine location of the Terraform statefile. Ensure that you define either '
                '"organization" and "workspace" (for Terraform Enterprise) or "statefile" (for S3 hosted '
                'Terraform state) in your "terraform:" section of deployfish.yml'
            )


class AbstractTerraformState(object):

    def __init__(self, terraform_config, context):
        self.context = context
        self.terraform_config = terraform_config
        self.loaded = False
        self.terraform_lookups = {}

    def load(self, replacements):
        raise NotImplementedError

    def lookup(self, attr, replacements):
        lookup_key = self.terraform_config['lookups'][attr]
        for key, value in replacements.items():
            lookup_key = lookup_key.replace(key, value)
        return self.terraform_lookups[lookup_key]['value']


class TerraformS3State(AbstractTerraformState):

    def __init__(self, terraform_config, context):
        super(TerraformS3State, self).__init__(terraform_config, context)
        self.replacements = None

    def _get_state_file_from_s3(self, state_file_url, profile=None, region=None):
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
            else:
                raise ex
        return json.loads(state_file)

    def _load_pre_version_12(self, tfstate):
        for i in tfstate['modules']:
            if i['path'] == [u'root']:
                for key, value in i['outputs'].items():
                    self.terraform_lookups[key] = value

    def _load_post_version_12(self, tfstate):
        for key, value in tfstate['outputs'].items():
            self.terraform_lookups[key] = value

    def load(self, replacements):
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
            major, minor, patch = tfstate['terraform_version'].split('.')
            if int(minor) >= 12:
                self._load_post_version_12(tfstate)
            else:
                self._load_pre_version_12(tfstate)
            # If our statefile URL has no replacments in it, we don't need to load this again
            self.loaded = not any([
                r in self.terraform_config['statefile'] for r in AbstractConfigProcessor.REPLACEMENTS
            ])


class TerraformEnterpriseState(AbstractTerraformState):

    TERRAFORM_API_ENDPOINT = 'https://app.terraform.io/api/v2'

    def __init__(self, terraform_config, context):
        super(TerraformEnterpriseState, self).__init__(terraform_config, context)
        if 'workspace' not in self.terraform_config:
            raise SchemaException(
                'In the "terraform:" section, if you define "organization", you must also define "workspace"'
            )
        if 'tfe_token' in self.context:
            self.api_token = self.context['tfe_token']
        if 'ATLAS_TOKEN' in os.environ:
            self.api_token = os.getenv('ATLAS_TOKEN')
        if not hasattr(self, 'tfe_token'):
            raise self.ProcessingFailed("Terraform Enterprise State: No Terraform Enterprise API token provided!")

    def get_terraform_state_download_url(self):
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

    def load(self, replacements):
        if not self.loaded:
            state_download_url = self.get_terraform_state_download_url()
            response = requests.get(state_download_url)
            tfstate = json.loads(response.text)
            for i in tfstate['modules']:
                if i['path'] == [u'root']:
                    for key, value in i['outputs'].items():
                        self.terraform_lookups[key] = value
            self.loaded = True


class TerraformStateConfigProcessor(AbstractConfigProcessor):

    TERRAFORM_RE = re.compile(r'\$\{terraform.(?P<key>[A-Za-z0-9_]+)\}')

    def __init__(self, config, context):
        super(TerraformStateConfigProcessor, self).__init__(config, context)
        try:
            self.terraform = TerraformStateFactory.new(config.raw['terraform'], context)
        except KeyError:
            raise self.SkipConfigProcessing('Skipping terraform state processing: no "terraform" section')

    def replace(self, obj, key, value, section_name, item_name):
        m = self.TERRAFORM_RE.search(value)
        if m:
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
