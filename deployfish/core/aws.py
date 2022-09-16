import os
from typing import Dict, Any, Optional, cast

import boto3
import yaml

from deployfish.exceptions import ConfigProcessingFailed


boto3_session: Optional[boto3.session.Session] = None


class AWSSessionBuilder:

    class NoSuchAWSProfile(Exception):
        pass

    class ForbiddenAWSAccountId(Exception):
        pass

    def load_config(self, filename: str) -> Dict[str, Any]:
        """
        Read our deployfish.yml file from disk and return it as parsed YAML.

        Args:
            filename: the path to our deployfish.yml file

        Returns:
            The data loaded from the YAML file.  This will not have any of the
            interpolations done.
        """
        if not os.path.exists(filename):
            return {}
        if not os.access(filename, os.R_OK):
            raise ConfigProcessingFailed(
                "Deployfish config file '{}' exists but is not readable".format(filename)
            )
        with open(filename, encoding='utf-8') as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def new(self, filename: str, use_aws_section: bool = True) -> boto3.session.Session:
        """
        Build and return a properly configured boto3 ``Session`` object.

        Args:
            filename: the path to our deployfish.yml file

        Keyword Args:
            use_aws_section: if ``False``, ignore any ``aws:`` section in deployfish.yml

        Raises:
            AWSSessionBuilder.NoSuchAWSProfile: the reqeusted profile is not in ``~/.aws/config``
            AWSSessionBuilder.ForbiddenAWSAccountId: the account id used by our profile is not allowed by
                our ``aws:`` section

        Returns:
            A configured boto3 ``Session`` object.
        """
        if not filename:
            filename = 'deployfish.yml'
        config = self.load_config(filename)
        if config and use_aws_section:
            aws_config = config.get('aws', {})
        else:
            aws_config = {}
        sess = self.__get_boto3_session(config=aws_config)
        if ('allowed_account_ids' in aws_config or 'forbidden_account_ids' in aws_config):
            account_id = sess.client('sts').get_caller_identity().get('Account')
            if 'allowed_account_ids' in aws_config:
                if account_id not in aws_config['allowed_account_ids']:
                    raise self.ForbiddenAWSAccountId(
                        f"Account ID {account_id} is not in the list of allowed_account_ids"
                    )
            if 'forbidden_account_ids' in aws_config:
                if account_id in aws_config['forbidden_account_ids']:
                    raise self.ForbiddenAWSAccountId(
                        f"Account ID {account_id} is in the list of forbidden_account_ids"
                    )
        return sess

    def __get_boto3_session(self, config: Dict[str, Any] = None) -> boto3.session.Session:
        if config:
            # If an API access key pair is provided in the 'aws' section, that
            # has priority
            if 'access_key' in config:
                session = boto3.session.Session(
                    aws_access_key_id=config.get('access_key'),
                    aws_secret_access_key=config.get('secret_key'),
                    region_name=config.get('region', None)
                )
            # If an AWS profile in the 'aws' section, that comes next
            elif 'profile' in config:
                profile = config.get('profile')
                if profile not in boto3.session.Session().available_profiles:
                    raise self.NoSuchAWSProfile("AWS profile '{}' does not exist in your ~/.aws/config".format(profile))
                session = boto3.session.Session(
                    profile_name=config.get('profile'),
                    region_name=config.get('region', None)
                )
            else:
                # We have an 'aws' section, but it has neither credentials nor
                # a profile, so possibly it just has a region.
                session = boto3.session.Session(
                    region_name=config.get('region', None)
                )
        else:
            # There was no 'aws' section in our config, so just leave it up to
            # the normal AWS credentials resolution
            session = boto3.session.Session()
        return session


def build_boto3_session(
    filename: str,
    boto3_session_override: boto3.session.Session = None,
    use_aws_section: bool = True
) -> None:
    global boto3_session  # pylint: disable=global-statement
    if boto3_session_override:
        boto3_session = boto3_session_override
    else:
        boto3_session = AWSSessionBuilder().new(filename, use_aws_section=use_aws_section)


def get_boto3_session(boto3_session_override: boto3.session.Session = None) -> boto3.session.Session:
    if boto3_session_override:
        return boto3_session_override
    if boto3_session:
        return boto3_session
    return cast(boto3.session.Session, boto3)
