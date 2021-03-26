from copy import copy
from datetime import datetime

import botocore

from .abstract import Manager, Model


# ----------------------------------------
# Mixinx
# ----------------------------------------

class SecretsMixin(object):

    def __init__(self, *args, **kwargs):
        super(SecretsMixin, self).__init__(*args, **kwargs)
        self.secrets = kwargs.pop('secrets', None)

    def get_secrets(self):
        return self.secrets

    def write_secrets(self):
        for secret in self.secrets:
            try:
                secret.save()
            except secret.ReadOnly:
                pass

    def diff_secrets(self):
        return [s.diff() for s in self.secrets()]


# ----------------------------------------
# Managers
# ----------------------------------------

class SecretManager(Manager):

    service = 'ssm'

    def __init__(self, model, readonly=False):
        self.model = model
        self.readonly = readonly

    def convert(self, parameter_data):
        data = {}
        data['Name'] = parameter_data['Name']
        data['Type'] = parameter_data['Type']
        data['Value'] = parameter_data['Value']
        if data['Type'] == 'SecureString':
            data['KeyId'] = parameter_data.get['KeyId']
        data['DataType'] = parameter_data.get('DataType', 'text')
        name = data['Name'].split('.')[-1]
        return self.model(data, name=name)

    def get(self, pk, **kwargs):
        secrets = self.list(pk)
        if not secrets:
            raise self.model.DoesNotExist(
                'No Parameter matching "{}" exists in AWS'.format(pk)
            )
        return secrets[0]

    def list(self, prefix):
        paginator = self.client.get_paginator('describe_parameters')
        response_iterator = paginator.paginate(Filters=[{'Key': 'Name', 'Values': prefix}])
        parameters = []
        for page in response_iterator:
            parameters.extend(page['Parameters'])
        secrets = []
        for parameter in parameters:
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
        except self.client.ParameterNotFound:
            raise Secret.DoesNotExist


# ----------------------------------------
# Models
# ----------------------------------------

class Secret(Model):

    objects = None

    class ReadOnlyException(Exception):
        pass

    def __init__(self, data, name=None):
        super(Secret, self).__init__(data)
        self.name = name

    @property
    def pk(self):
        return self.data['Name']

    @property
    def value(self):
        return self.data['Value']

    def render_for_create(self):
        data = self.render()
        data['Overwrite'] = True
        return data


class ExternalSecret(Secret):

    objects = None


Secret.objects = SecretManager(Secret)
objects = SecretManager(ExternalSecret, readonly=True)
