import boto3
import os

import yaml

from deployfish.exceptions import ConfigProcessingFailed


boto3_session = None


class AWSSessionBuilder(object):

    class NoSuchAWSProfile(Exception):
        pass

    class ForbiddenAWSAccountId(Exception):
        pass

    def load_config(self, filename):
        """
        Read our deployfish.yml file from disk and return it as parsed YAML.

        :param filename: the path to our deployfish.yml file
        :type filename: string

        :rtype: dict
        """
        if not os.path.exists(filename):
            return {}
        elif not os.access(filename, os.R_OK):
            raise ConfigProcessingFailed(
                "Deployfish config file '{}' exists but is not readable".format(filename)
            )
        with open(filename) as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def new(self, filename, use_aws_section=True):
        if not filename:
            filename = 'deployfish.yml'
        config = self.load_config(filename)
        if config and use_aws_section:
            aws_config = config.get('aws', {})
        else:
            aws_config = {}
        boto3_session = self.__get_boto3_session(config=aws_config)
        if ('allowed_account_ids' in aws_config or 'forbidden_account_ids' in aws_config):
            account_id = boto3_session.client('sts').get_caller_identity().get('Account')
            if 'allowed_account_ids' in aws_config:
                if account_id not in aws_config['allowed_account_ids']:
                    raise self.ForbiddenAWSAccountId(
                        "Account ID {} is not in the list of allowed_account_ids".format(account_id)
                    )
            if 'forbidden_account_ids' in aws_config:
                if account_id in aws_config['forbidden_account_ids']:
                    raise self.ForbiddenAWSAccountId(
                        "Account ID {} is in the list of forbidden_account_ids".format(account_id)
                    )
        return boto3_session

    def __get_boto3_session(self, config=None):
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

    def __get_account_id(self):
        return self.boto3_session.client('sts').get_caller_identity().get('Account')


def build_boto3_session(filename, boto3_session_override=None, use_aws_section=True):
    global boto3_session
    if boto3_session_override:
        boto3_session = boto3_session_override
    else:
        boto3_session = AWSSessionBuilder().new(filename, use_aws_section=use_aws_section)


def get_boto3_session(boto3_session_override=None):
    if boto3_session_override:
        return boto3_session_override
    global boto3_session
    if boto3_session:
        return boto3_session
    else:
        return boto3
