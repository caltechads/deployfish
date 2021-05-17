import json

from jsondiff import diff

from .abstract import Manager, Model


# ----------------------------------------
# Mixinx
# ----------------------------------------

class SecretsMixin(object):

    @property
    def secrets_prefix(self):
        raise NotImplementedError

    @property
    def secrets(self):
        return self.cache['secrets']

    @secrets.setter
    def secrets(self, value):
        self.cache['secrets'] = value

    def write_secrets(self):
        # Add and update secrets we do need
        for secret in self.secrets.values():
            try:
                secret.save()
            except secret.ReadOnly:
                pass
        # now delete any secrets that we no longer need
        if self.secrets:
            aws_pks = Secret.objects.list_names(self.secrets_prefix)
            our_pks = [s.pk for s in self.secrets.values()]
            for_deletion = list(set(aws_pks) - set(our_pks))
            if for_deletion:
                Secret.objects.delete_many_by_name(for_deletion)

    def reload_secrets(self):
        if 'secrets' in self.cache:
            del self.cache['secrets']

    def diff_secrets(self, other, ignore_external=False):
        """
        Diff our list of Secrets against `other`.

        `other` is either a list of Secrets and ExternalSecrets, or is a dict where
        the key is the Secret name and the value is the Secret object.
        """
        us = {}
        them = {}
        if isinstance(other, dict):
            other = other.values()
        if ignore_external:
            other = [s for s in other if not isinstance(s, ExternalSecret)]
        if self.secrets:
            our_secrets = sorted(self.secrets.values(), key=lambda x: x.name)
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

    def __init__(self, model, readonly=False):
        self.model = model
        self.readonly = readonly
        super(SecretManager, self).__init__()

    def _describe_parameters(self, key, option='prefix'):
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

    def _get_parameter_values(self, names):
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

    def convert(self, parameter_data):
        name = parameter_data['Name'].split('.')[-1]
        return self.model(parameter_data, name=name)

    def get(self, pk, **kwargs):
        values, non_existant_parameters = self._get_parameter_values([pk])
        params = self._describe_parameters(pk, option='equals')
        if non_existant_parameters:
            raise Secret.DoesNotExist('No secret named {} exists in AWS'.format(pk))
        data = params[0]
        data['ARN'] = values[pk]['ARN']
        data['Value'] = values[pk]['Value']
        return self.convert(data)

    def get_many(self, pks, **kwargs):
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
        for name, data in descriptions.items():
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

    def list_names(self, prefix):
        if prefix.endswith('*'):
            prefix = prefix[:-1]
            if not prefix.endswith('.'):
                prefix = prefix + "."
        parameters = self._describe_parameters(prefix)
        return [p['Name'] for p in parameters]

    def list(self, prefix):
        if prefix.endswith('*'):
            prefix = prefix[:-1]
            if not prefix.endswith('.'):
                prefix = prefix + "."
        parameters = self._describe_parameters(prefix)
        # We have to do two loops here, because describe_parameters gives us the KeyId for our KMS key, but does not
        # give us Value or ARN, while get_parameters gives us Value and ARN but no KeyId
        names = [parameter['Name'] for parameter in parameters]
        values, _ = self._get_parameter_values(names)
        secrets = []
        for parameter in parameters:
            parameter['ARN'] = values[parameter['Name']]['ARN']
            parameter['Value'] = values[parameter['Name']]['Value']
            secrets.append(self.convert(parameter))
        return secrets

    def save(self, obj):
        if not self.readonly:
            response = self.client.put_parameter(**obj.render_for_create())
            return response['Version']
        raise self.model.ReadOnly('This Secret is read only.')

    def delete_many_by_name(self, pks):
        # hint: (list[str["{secret_pk}"]])
        self.client.delete_parameters(Names=pks)

    def delete(self, obj):
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

    objects = None

    class DecryptionFailed(Exception):
        pass

    def __init__(self, data, name=None):
        super(Secret, self).__init__(data)
        self.secret_name = name

    @property
    def pk(self):
        return self.data['Name']

    @property
    def name(self):
        return self.secret_name

    @property
    def arn(self):
        return self.data.get('ARN', None)

    @property
    def prefix(self):
        return self.data['Name'].rsplit('.', 1)[0]

    @prefix.setter
    def prefix(self, value):
        self.data['Name'] = '{}.{}'.format(value, self.secret_name)

    @property
    def is_secure(self):
        return self.kms_key_id is not None

    @property
    def modified_username(self):
        user = self.data.get('LastModifiedUser', None)
        if user:
            return user.rsplit('/', 1)[1]
        else:
            return None

    @property
    def kms_key_id(self):
        return self.data.get('KeyId', None)

    @kms_key_id.setter
    def kms_key_id(self, value):
        self.data['Type'] = 'SecureString'
        self.data['KeyId'] = value

    @property
    def value(self):
        return self.data['Value']

    @value.setter
    def value(self, value):
        self.data['Value'] = value

    def render_for_create(self):
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

    def copy(self):
        data = self.render()
        if 'ARN' in data:
            del data['ARN']
            del data['LastModifiedDate']
            del data['LastModifiedUser']
            del data['Version']
        obj = self.__class__(data)
        obj.secret_name = self.secret_name
        return obj

    def __str__(self):
        line = '{}={}'.format(self.secret_name, self.value)
        if self.data['Type'] == 'SecureString':
            line += " [SECURE:{}]".format(self.kms_key_id)
        return line


class ExternalSecret(Secret):

    objects = None


Secret.objects = SecretManager(Secret)
ExternalSecret.objects = SecretManager(ExternalSecret, readonly=True)
