import string
import re

import boto3


class KeyPrefixMixin(object):

    @property
    def name_prefix(self):
        return "{}.{}.".format(self.cluster, self.service)


class Parameter(KeyPrefixMixin):
    """
    This class represents a parameter in the AWS Systems Manager Parameter Store.
    """

    def __init__(self, service, cluster, aws={}, yml=None):
        self.ssm = boto3.client('ssm')
        self.service = service
        self.cluster = cluster
        self.__defaults()
        self.__from_yml(yml)
        self.__from_aws(aws)

    def __defaults(self):
        self._value = None
        self._key = None
        self.kms_key_id = None
        self.is_external = False
        self._is_secure = False

    @property
    def name(self):
        """
        Return the full name of the parameter as we will store it in AWS.

        :rtype: string
        """
        return self.name_prefix + self.key

    @property
    def value(self):
        """
        Return the value of the parameter as it is in AWS.

        :rtype: string
        """
        if not self._value:
            if self.__aws_parameter:
                self._value = self.__aws_parameter['Value']
        return self._value

    @property
    def aws_value(self):
        if self.__aws_parameter:
            return self.__aws_parameter['Value']
        else:
            raise ValueError

    @property
    def key(self):
        """
        Return the parameter key as it is in AWS.

        :rtype: string
        """
        if not self._key:
            if self.__aws_parameter:
                self._key = self.__aws_parameter['Name'][len(self.name_prefix):]

        # strip the external prefix
        if self.is_external:
            key = self._key.split('.')[-1]
            return key
        return self._key

    @property
    def is_secure(self):
        """
        Return ``True`` if we want the value for this parameter to be encrypted
        in AWS, ``False`` otherwise.

        :rtype: boolean
        """
        if not self.__yml:
            if self.__aws_parameter:
                self._is_secure = self.__aws_parameter['Type'] == "SecureString"
        return self._is_secure

    @property
    def exists(self):
        """
        Return ``True`` if the parameter exists in AWS, ``False`` otherwise.

        :rtype: boolean
        """
        return self.__aws_parameter != {}

    @property
    def should_exist(self):
        """
        Return ``True`` if we want this parameter to exist in AWS.  This means that
        we have a parameter definition for this parameter in our ``deployfish.yml``
        file.

        This will always return ``True`` for external parameters.

        :rtype: boolean
        """
        if self.is_external:
            return True
        return self.__yml is not None

    @property
    def needs_update(self):
        """
        Return ``True`` if the value portion of our parameter definition differs
        from what is currently in AWS, ``False`` otherwise.

        This will always be ``False`` for external parameters.

        :rtype: boolean
        """
        if self.is_external:
            return False
        if not self.__aws_parameter:
            return True
        else:
            return self.value != self.__aws_parameter['Value']

    def _split(self, definition):
        """
        In our YAML parameter definition line, split the key part from the value part.

        :param definition: a parameter definition from our deployfish.yml
        :type definition: string

        :rtype: 2-tuple of strings
        """
        key = definition
        value = None
        delimiter_loc = definition.find('=')
        if delimiter_loc > 0:
            key = definition[:delimiter_loc]
            if len(definition) > delimiter_loc + 1:
                value = definition[delimiter_loc + 1:].strip('"')
            else:
                value = ""
        return (key, value)

    def _parse_key(self, key):
        """
        Parse a key from a parameter definition that looks like one of the following:

            KEY
            KEY:secure
            KEY:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
            KEY:external
            KEY:external:secure
            KEY:external:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
        """
        i = 0
        while key is not None:
            # segments = string.split(key, ':', 1)
            segments = key.split(':', 1)
            segment = segments[0]
            if len(segments) > 1:
                key = segments[1]
            else:
                key = None
            if i == 0:
                self._key = segment
            elif segment == 'external':
                self.is_external = True
            elif segment == 'secure':
                self._is_secure = True
            elif segment == 'arn':
                self.kms_key_id = 'arn:{}'.format(key)
                break
            i += 1

    def __from_yml(self, yml=None):
        """
        Parse a parameter definition string and set some instance properties based on it.

        If ``yml`` is not ``None``, it will be a string that looks like one of the following examples:

            KEY=value
            KEY:secure=value
            KEY:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=value
            KEY:external
            KEY:external:secure
            KEY:external:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

        :param yml: (optional) a string describing a parameter to be stored in
                    AWS Systems Manager Parameter Store
        :type yml: string
        """
        if yml:
            self.__yml = yml
            key, value = self._split(yml)
            self._value = value
            self._parse_key(key)
            if not self._value and not self.is_external:
                raise ValueError
        else:
            self.__yml = None

    def _render_read(self):
        """
        Create an list of keyword parameters suitable for passing to
        ``boto3.client('ssm').get_parameters()``.

        :rtype: dict
        """
        d = {}
        if self.is_external:
            d['Names'] = [self._key]
        else:
            d['Names'] = ["{}.{}.{}".format(self.cluster, self.service, self.key)]
        d['WithDecryption'] = True
        return d

    def __from_aws(self, aws=None):
        """
        Return the current value of the parameter named by ``self.key`` as it
        exists in AWS.  If such a parameter does not exist, raise ``KeyError``.
        """
        self.__aws_parameter = aws
        if not aws:
            response = self.ssm.get_parameters(**self._render_read())
            if response['Parameters']:
                self.__aws_parameter = response['Parameters'][0]

    def _render_write(self):
        """
        Create an list of keyword parameters suitable for passing to
        ``boto3.client('ssm').put_parameter()``.

        :rtype: dict
        """
        d = {}
        d['Name'] = "{}.{}.{}".format(self.cluster, self.service, self.key)
        d['Value'] = self.value
        d['Overwrite'] = True
        if self.is_secure:
            d['Type'] = 'SecureString'
            if self.kms_key_id:
                d['KeyId'] = self.kms_key_id
        else:
            d['Type'] = 'String'
        return d

    def save(self):
        """
        If the value still exists in the config, save it, otherwise remove the parameter
        from AWS
        """
        if self.should_exist:
            if self.needs_update and not self.is_external:
                self.ssm.put_parameter(**self._render_write())
        elif self.exists:
            self.ssm.delete_parameter(Name=self.name)

    def display(self, key, value):
        """
        Return a human readable display of the key value pair
        :param key:
        :param value:
        :return: string
        """
        base = "{}: {}".format(key, value)
        if self.is_external:
            base += " [EXTERNAL]"
        if self.is_secure:
            base += " [SECURE:{}]".format(self.kms_key_id)
        return base

    def __str__(self):
        return self.display(self.key, self.value)


class ParameterFactory(object):

    WILDCARE_RE = re.compile('^(?P<key>.+\..+\.)\*(?P<remainder>.*)')

    @staticmethod
    def new(service, cluster, yml=None):
        """
        Returns a list of parameters.
        :param service:
        :param cluster:
        :param yml:
        :return: list
        """
        if yml:
            m = ParameterFactory.WILDCARE_RE.search(yml)
            if m:
                parameter_list = []
                ssm = boto3.client('ssm')
                response = ssm.describe_parameters(Filters=[{'Key': 'Name', 'Values': [m.group('key')]}], MaxResults=50)
                parms = response['Parameters']
                for parm in parms:
                    if parm['Type'] == 'SecureString':
                        line = "{}:external:secure:{}".format(parm['Name'], parm['KeyId'])
                    else:
                        line = "{}:external".format(parm['Name'])
                    parameter_list.append(Parameter(service, cluster, yml=line))
                return parameter_list

        return [Parameter(service, cluster, yml=yml)]


class ParameterStore(KeyPrefixMixin, list):

    """
    This class is the access point for parameters in the AWS System Manager Parameter Store.
    """

    def __init__(self, service, cluster, yml=[]):
        super(ParameterStore, self).__init__()
        self.service = service
        self.cluster = cluster
        self.yml = yml
        self.populated = False

    def populate(self):
        """
        Lazy loading function to load the values from AWS.
        """
        if self.populated:
            return

        self.ssm = boto3.client('ssm')
        self.from_yaml(self.yml)
        self.from_aws()
        self.populated = True

    def from_yaml(self, yml):
        """
        Construct the Parameter objects as configured in the YAML file.
        :param yml:
        """
        for definition in yml:
            self.extend(ParameterFactory.new(self.service, self.cluster, yml=definition))

    def from_aws(self):
        """
        Find parameter stores currently in the AWS System Manager Parameter Store that
        should be deleted.  These will have our parameter name prefix ("CLUSTER.SERVICE.")
        """
        response = self.ssm.describe_parameters(
            Filters=[
                {
                    'Key': 'Name',
                    'Values': [self.name_prefix]
                }
            ],
            MaxResults=50
        )
        for parameter in response['Parameters']:
            if parameter['Name'] not in self:
                response = self.ssm.get_parameters(Names=[parameter['Name']], WithDecryption=True)
                self.append(Parameter(self.service, self.cluster, aws=response['Parameters'][0]))

    def save(self):
        """
        Save all of the parameters in AWS.
        """
        self.populate()
        for parm in self:
            parm.save()

    def __contains__(self, key):
        for parameter in self:
            if parameter.name == key:
                return True
        return False
