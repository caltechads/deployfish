import boto3


boto3_session = None


class AWSSessionBuilder(object):

    class NoSuchAWSProfile(Exception):
        pass

    class ForbiddenAWSAccountId(Exception):
        pass

    def new(self, config=None):
        aws_config = {}
        if config:
            try:
                aws_config = config.get_section('aws')
            except KeyError:
                pass
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


def build_boto3_session(config=None, boto3_session_override=None):
    global boto3_session
    if boto3_session_override:
        boto3_session = boto3_session_override
    else:
        boto3_session = AWSSessionBuilder().new(config)


def get_boto3_session(boto3_session_override=None):
    if boto3_session_override:
        return boto3_session_override
    global boto3_session
    if boto3_session:
        return boto3_session
    else:
        return boto3
