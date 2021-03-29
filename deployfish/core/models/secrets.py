from jsondiff import diff

from .abstract import Manager, Model


# ----------------------------------------
# Mixinx
# ----------------------------------------

class SecretsMixin(object):

    @property
    def secrets(self):
        return self.cache['secrets']

    @secrets.setter
    def secrets(self, value):
        self.cache['secrets'] = value

    def write_secrets(self):
        for secret in self.secrets:
            try:
                secret.save()
            except secret.ReadOnly:
                pass

    def diff_secrets(self, other):
        """
        Diff our list of Secrets against `other`, another list of Secrets.

        :param other List[Union[Secret, ExternalSecret]]
        """
        us, them = {}
        if self.secrets:
            us = {s.name: s.render_for_diff() for s in self.secrets}
        if other:
            them = {s.name: s.render_for_diff() for s in other}
        return diff(us, them)


# ----------------------------------------
# Managers
# ----------------------------------------

class SecretManager(Manager):

    service = 'ssm'

    def __init__(self, model, readonly=False):
        self.model = model
        self.readonly = readonly
        super(SecretManager, self).__init__()

    def _describe_parameters(self, prefix):
        paginator = self.client.get_paginator('describe_parameters')
        response_iterator = paginator.paginate(
            ParameterFilters=[
                {'Key': 'Name', 'Option': 'BeginsWith', 'Values': [prefix]}
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
        for chunk in names_chunks:
            try:
                response = self.client.get_parameters(Names=chunk, WithDecryption=True)
            except self.client.exceptions.InvalidKeyId as e:
                raise self.model.DecryptionFailed(str(e))
            if 'InvalidParameters' in response and response['InvalidParameters']:
                raise self.model.DoesNotExist(
                    'These SSM Parameter Store parameters do not exist in AWS: {}'.format(
                        ', '.join(response['InvalidParameters'])
                    )
                )
            parameters.extend(response['Parameters'])
        return {p['Name']: p for p in parameters}

    def convert(self, parameter_data):
        name = parameter_data['Name'].split('.')[-1]
        return self.model(parameter_data, name=name)

    def get(self, pk, **kwargs):
        return self.get_many([pk])[0]

    def get_many(self, pks, **kwargs):
        values = self._get_parameter_values(pks)
        prefixes = set()
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
        return secrets

    def list(self, prefix):
        parameters = self._describe_parameters(prefix)
        # We have to do two loops here, because describe_parameters gives us the KeyId for our KMS key, but does not
        # give us Value or ARN, while get_parameters gives us Value and ARN but no KeyId
        names = [parameter['Name'] for parameter in parameters]
        values = self._get_parameter_values(names)
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
    def value(self):
        return self.data['Value']

    def render_for_create(self):
        data = self.render()
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
        return data


class ExternalSecret(Secret):

    objects = None


Secret.objects = SecretManager(Secret)
ExternalSecret.objects = SecretManager(ExternalSecret, readonly=True)
