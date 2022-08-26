from copy import deepcopy
from typing import Dict, Any, Tuple, List, cast

from deployfish.core.models import Secret, ExternalSecret

from ..abstract import Adapter


def parse_secret_string(secret_string: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse an identifier from a deployfish.yml parameter definition that looks like one of the following:

        KEY=VALUE
        KEY:secure=VALUE
        KEY:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=VALUE
    """
    i = 0
    key = ''
    is_secure = False
    kms_key_id = None
    identifier, value = deepcopy(secret_string).split('=', 1)
    while identifier is not None:
        segments = identifier.split(':', 1)
        segment = segments[0]
        if i == 0:
            key = segment
        elif segment == 'secure':
            is_secure = True
        elif segment == 'arn':
            kms_key_id = 'arn:{}'.format(segments[1])
            break
        if len(segments) > 1:
            identifier = segments[1]
        else:
            break
        i += 1
    kwargs: Dict[str, Any] = {
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


# ------------------------
# Mixins
# ------------------------

class SecretsMixin:

    data: Dict[str, Any]

    def get_secrets(self, cluster: str, name: str) -> List[Secret]:
        secrets = None
        if 'config' in self.data:
            secrets = []
            for secret in self.data['config']:
                try:
                    secrets.append(Secret.new({'value': secret}, 'deployfish', cluster=cluster, name=name))
                except SecretAdapter.ExternalParameterException:
                    # handle globs
                    secrets.extend(ExternalSecret.objects.list(secret))
        return cast(List[Secret], secrets)


# ------------------------
# Adapters
# ------------------------

class SecretAdapter(Adapter):

    class ExternalParameterException(Exception):
        pass

    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(data, **kwargs)
        self.cluster: str = kwargs.pop('cluster', None)
        self.name: str = kwargs.pop('name', None)
        self.prefix: str = ''
        if 'prefix' in kwargs and kwargs['prefix']:
            self.prefix = '{}-'.format(kwargs['prefix'])

    def is_external(self) -> bool:
        if ('=' not in self.data['value'] or ':external' in self.data['value']):
            return True
        return False

    def split(self) -> Tuple[str, str]:
        definition: str = deepcopy(self.data['value'])
        key = definition
        value = ""
        delimiter_loc = definition.find('=')
        if delimiter_loc > 0:
            key = definition[:delimiter_loc]
            if len(definition) > delimiter_loc + 1:
                value = definition[delimiter_loc + 1:].strip('"')
        return key, value

    def parse(self) -> Tuple[str, Dict[str, Any]]:
        """
        Parse an identifier from a deployfish.yml parameter definition that looks like one of the following:

            KEY=VALUE
            KEY:secure=VALUE
            KEY:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=VALUE
        """
        return parse_secret_string(self.data['value'])

    def convert(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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
