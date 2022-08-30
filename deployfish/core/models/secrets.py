import sys
import json
from typing import Dict, Any, Sequence, List, Union, Type, Tuple, Optional

from jsondiff import diff

from deployfish.types import SupportsCache

from .abstract import Manager, Model

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


# ----------------------------------------
# Protocols
# ----------------------------------------

class SupportsSecrets(SupportsCache, Protocol):

    @property
    def secrets_prefix(self) -> str:
        ...

    @property
    def secrets(self) -> Dict[str, "Secret"]:
        ...



# ----------------------------------------
# Mixins
# ----------------------------------------

class SecretsMixin:

    @property
    def secrets_prefix(self) -> str:
        raise NotImplementedError

    @property
    def secrets(self: SupportsSecrets) -> Dict[str, "Secret"]:
        return self.cache['secrets']

    @secrets.setter
    def secrets(self: SupportsSecrets, value: Dict[str, "Secret"]) -> None:
        self.cache['secrets'] = value

    def write_secrets(self: SupportsSecrets) -> None:
        # Add and update secrets we do need
        for secret in list(self.secrets.values()):
            try:
                secret.save()
            except secret.ReadOnly:
                pass
        # now delete any secrets that we no longer need
        if self.secrets:
            aws_pks = Secret.objects.list_names(self.secrets_prefix)
            our_pks = [s.pk for s in list(self.secrets.values())]
            for_deletion = list(set(aws_pks) - set(our_pks))
            if for_deletion:
                Secret.objects.delete_many_by_name(for_deletion)

    def reload_secrets(self: SupportsSecrets) -> None:
        if 'secrets' in self.cache:
            del self.cache['secrets']

    def diff_secrets(self: SupportsSecrets, other: Sequence["Secret"], ignore_external: bool = False) -> Dict[str, Any]:
        """
        Diff our list of Secrets against `other`.

        `other` is either a list of Secrets and ExternalSecrets, or is a dict where
        the key is the Secret name and the value is the Secret object.
        """
        us = {}
        them = {}
        if isinstance(other, dict):
            other = list(other.values())
        if ignore_external:
            other = [s for s in other if not isinstance(s, ExternalSecret)]
        if self.secrets:
            our_secrets = sorted(list(self.secrets.values()), key=lambda x: x.name)
            if ignore_external:
                our_secrets = [s for s in our_secrets if not isinstance(s, ExternalSecret)]
            us = {s.name: s.render_for_diff() for s in our_secrets}
        if other:
            their_secrets = sorted(other, key=lambda x: x.name)
            them = {s.name: s.render_for_diff() for s in their_secrets}
        return json.loads(diff(them, us, syntax='explicit', dump=True))


# ----------------------------------------
# Managers
# ----------------------------------------

class SecretManager(Manager):

    service = 'ssm'

    def __init__(self, model: Union[Type["Secret"], Type["ExternalSecret"]], readonly: bool = False) -> None:
        self.model = model
        self.readonly = readonly
        super().__init__()

    def _describe_parameters(self, key: str, option: str = 'prefix') -> List[Dict[str, Any]]:
        if option == 'prefix':
            option = 'BeginsWith'
        else:
            option = 'Equals'
        paginator = self.client.get_paginator('describe_parameters')
        response_iterator = paginator.paginate(
            ParameterFilters=[
                {'Key': 'Name', 'Option': option, 'Values': [key]}
            ]
        )
        parameters = []
        for page in response_iterator:
            parameters.extend(page['Parameters'])
        return parameters

    def _get_parameter_values(self, names: List[str]) -> Tuple[Dict[str, Any], List[str]]:
        # get_parameters only accepts 10 or fewer names in the Names kwarg, so we have to
        # split names into sub lists of 10 of fewer names and iterate
        names_chunks = [names[i * 10:(i + 1) * 10] for i in range((len(names) + 9) // 10)]
        parameters = []
        non_existant = []
        for chunk in names_chunks:
            try:
                response = self.client.get_parameters(Names=chunk, WithDecryption=True)
            except self.client.exceptions.InvalidKeyId as e:
                raise self.model.DecryptionFailed(str(e))
            if 'InvalidParameters' in response and response['InvalidParameters']:
                non_existant.extend(response['InvalidParameters'])
            parameters.extend(response['Parameters'])
        return {p['Name']: p for p in parameters}, non_existant

    def convert(self, parameter_data: Dict[str, Any]) -> "Secret":
        name = parameter_data['Name'].split('.')[-1]
        return self.model(parameter_data, name=name)

    def get(self, pk: str, **_) -> "Secret":
        values, non_existant_parameters = self._get_parameter_values([pk])
        params = self._describe_parameters(pk, option='equals')
        if non_existant_parameters:
            raise Secret.DoesNotExist('No secret named {} exists in AWS'.format(pk))
        data = params[0]
        data['ARN'] = values[pk]['ARN']
        data['Value'] = values[pk]['Value']
        return self.convert(data)

    def get_many(self, pks: List[str], **_) -> Sequence["Secret"]:
        """

        .. note::

            What we want to return is data that contains both the encryption information (which is only
            available from describe_paramters) and the actual parameter value (which is only available
            from get_parameters).  So we do one call to describe_parameters and one to get_parameters for
            each parameter (well, we bundle the calls as much as possible) and combine the results.
        """
        # Use get_parameter to get the parameter values
        values, non_existant_parameters = self._get_parameter_values(pks)
        prefixes = set()
        # FIXME: we're getting all parameters for a service even if we wanted just a few, and that takes a long time.
        # Find the breakeven point below which it's faster to get parameters individually and above which is better to
        # get all the paramters.
        for pk in pks:
            prefixes.add(pk.rsplit('.', 1)[0])
        descriptions = {}
        for prefix in prefixes:
            params = self._describe_parameters(prefix)
            for p in params:
                descriptions[p['Name']] = p
        secrets = []
        for name, data in list(descriptions.items()):
            if name in values:
                data['ARN'] = values[name]['ARN']
                data['Value'] = values[name]['Value']
            secrets.append(self.convert(data))
        # Fake the non-existant parameters
        for param in non_existant_parameters:
            data = {
                'Name': param,
                'Type': 'String',
                'Tier': 'Standard'
            }
            secrets.append(self.convert(data))
        return secrets

    def list_names(self, prefix: str) -> List[str]:
        if prefix.endswith('*'):
            prefix = prefix[:-1]
            if not prefix.endswith('.'):
                prefix = prefix + "."
        parameters = self._describe_parameters(prefix)
        return [p['Name'] for p in parameters]

    def list(self, prefix: str) -> Sequence["Secret"]:
        if prefix.endswith('*'):
            prefix = prefix[:-1]
            if not prefix.endswith('.'):
                prefix = prefix + "."
        parameters = self._describe_parameters(prefix)
        # We have to do two loops here, because describe_parameters gives us the
        # KeyId for our KMS key, but does not give us Value or ARN, while
        # get_parameters gives us Value and ARN but no KeyId
        names = [parameter['Name'] for parameter in parameters]
        values, _ = self._get_parameter_values(names)
        secrets = []
        for parameter in parameters:
            parameter['ARN'] = values[parameter['Name']]['ARN']
            parameter['Value'] = values[parameter['Name']]['Value']
            secrets.append(self.convert(parameter))
        return secrets

    def save(self, obj: Model, **_) -> str:
        if not self.readonly:
            response = self.client.put_parameter(**obj.render_for_create())
            return response['Version']
        raise self.model.ReadOnly('This Secret is read only.')

    def delete_many_by_name(self, pks: List[str]) -> None:
        if len(pks) <= 10:
            self.client.delete_parameters(Names=pks)
        else:
            # delete_parameters() will only take 10 params at a time, so we have
            # to split it up if we have more than 10
            chunks = [pks[i * 10:(i + 1) * 10] for i in range((len(pks) + 9) // 10)]
            for chunk in chunks:
                self.client.delete_parameters(Names=chunk)

    def delete(self, obj: Model, **_) -> None:
        if self.readonly:
            raise self.model.ReadOnly('This Secret is read only.')
        try:
            self.client.delete_parameter(Name=obj.pk)
        except self.client.exceptions.ParameterNotFound:
            raise Secret.DoesNotExist


# ----------------------------------------
# Models
# ----------------------------------------

class Secret(Model):
    """
    An SSM Parameter Store Parameter.
    """

    objects: SecretManager

    class DecryptionFailed(Exception):
        pass

    def __init__(self, data: Dict[str, Any], name: str = ''):
        super().__init__(data)
        self.secret_name = name

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data['Name']

    @property
    def name(self) -> str:
        return self.secret_name

    @property
    def arn(self) -> str:
        return self.data.get('ARN', None)

    def render_for_create(self) -> Dict[str, Any]:
        data = self.render()
        if 'ARN' in data:
            del data['ARN']
            del data['LastModifiedDate']
            del data['LastModifiedUser']
            del data['Version']
        data['Overwrite'] = True
        return data

    def render_for_diff(self):
        data = self.render()
        data['EnvVar'] = self.secret_name
        if 'ARN' in data:
            del data['ARN']
            del data['LastModifiedDate']
            del data['LastModifiedUser']
            del data['Version']
            del data['Policies']
        return data

    # ----------------------------
    # Secret-specific properties
    # ----------------------------

    @property
    def prefix(self) -> str:
        return self.data['Name'].rsplit('.', 1)[0]

    @prefix.setter
    def prefix(self, value: str) -> None:
        self.data['Name'] = f'{value}.{self.secret_name}'

    @property
    def is_secure(self) -> bool:
        return self.kms_key_id is not None

    @property
    def modified_username(self) -> Optional[str]:
        user = self.data.get('LastModifiedUser', None)
        if user:
            return user.rsplit('/', 1)[1]
        return None

    @property
    def kms_key_id(self) -> str:
        return self.data.get('KeyId', None)

    @kms_key_id.setter
    def kms_key_id(self, value: str) -> None:
        self.data['Type'] = 'SecureString'
        self.data['KeyId'] = value

    @property
    def value(self) -> str:
        return self.data['Value']

    @value.setter
    def value(self, value: str) -> None:
        self.data['Value'] = value

    # ------------------------
    # Secret-specific actions
    # ------------------------

    def copy(self) -> "Secret":
        data = self.render()
        if 'ARN' in data:
            del data['ARN']
            del data['LastModifiedDate']
            del data['LastModifiedUser']
            del data['Version']
        obj = self.__class__(data, self.secret_name)
        return obj

    def __str__(self) -> str:
        line = f'{self.secret_name}={self.value}'
        if self.data['Type'] == 'SecureString':
            line = f"{line} [SECURE:{self.kms_key_id}]"
        return line


class ExternalSecret(Secret):

    objects: SecretManager


Secret.objects = SecretManager(Secret)
ExternalSecret.objects = SecretManager(ExternalSecret, readonly=True)
