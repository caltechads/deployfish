from copy import copy

from deployfish.core.models import Secret, ExternalSecret

from .mixins import DeployfishYamlAdapter


# ------------------------
# Mixins
# ------------------------

class SecretsMixin:

    def get_secrets(self, cluster, name, prefix=''):
        secrets = None
        if 'config' in self.data:
            secrets = []
            for secret in self.data['config']:
                try:
                    secrets.append(Secret.new(secret, 'deployfish', cluster=cluster, name=name, prefix=prefix))
                except SecretAdapter.ExternalParameterException:
                    # handle globs
                    if secret.endswith('*'):
                        secret = secret[:-1]
                    secrets.extend(ExternalSecret.objects.list(secret))
        return secrets


# ------------------------
# Adapters
# ------------------------

class SecretAdapter(DeployfishYamlAdapter):

    class ExternalParameterException(Exception):
        pass

    def __init__(self, data, **kwargs):
        super(SecretAdapter, self).__init__(data, **kwargs)
        self.cluster = kwargs.pop('cluster', None)
        self.name = kwargs.pop('name', None)
        if 'prefix' in kwargs and kwargs['prefix']:
            self.prefix = '{}-'.format(kwargs['prefix'])
        else:
            self.prefix = ''

    def is_external(self):
        if ':external' in self.data:
            return True
        return False

    def split(self):
        definition = copy(self.data)
        key = definition
        value = None
        delimiter_loc = definition.find('=')
        if delimiter_loc > 0:
            key = definition[:delimiter_loc]
            if len(definition) > delimiter_loc + 1:
                value = definition[delimiter_loc + 1:].strip('"')
            else:
                value = ""
        return key, value

    def parse(self):
        """
        Parse an identifier from a deployfish.yml parameter definition that looks like one of the following:

            KEY
            KEY:secure
            KEY:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
            KEY:external
            KEY:external:secure
            KEY:external:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
        """
        i = 0
        key = None
        is_secure = False
        kms_key_id = None

        identifier, value = copy(self.data).split('=', 1)
        while identifier is not None:
            segments = identifier.split(':', 1)
            segment = segments[0]
            if len(segments) > 1:
                identifier = segments[1]
            else:
                identifier = None
            if i == 0:
                key = segment
            elif segment == 'secure':
                is_secure = True
            elif segment == 'arn':
                kms_key_id = 'arn:{}'.format(key)
                break
            i += 1
        kwargs = {
            'Value': value,
            'DataType': 'text',
            'Tier': 'Standard'
        }
        if is_secure:
            kwargs['Type'] = 'SecureString'
            kwargs['KeyId'] = kms_key_id
        else:
            kwargs['Type'] = 'String'
        return key, kwargs

    def convert(self):
        if self.is_external():
            raise self.ExternalParameterException(
                'This is an external parameter; use ExternalParametersAdapter instead'
            )
        key, kwargs = self.parse()
        data = {}
        if self.cluster and self.name:
            data['Name'] = '{}{}.{}.{}'.format(self.prefix, self.cluster, self.name, key)
        else:
            data['Name'] = '{}{}'.format(self.prefix, key)
        data.update(kwargs)

        return data, {'name': key}
