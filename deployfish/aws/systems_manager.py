import re

from deployfish.aws import get_boto3_session

WILDCARD_RE = re.compile('^(?P<prefix>.+\..+\.)\*(?P<remainder>.*)')


class BaseParameter(object):
    """
    This class represents a parameter in the AWS Systems Manager Parameter Store.
    """

    def __init__(self, name, kms_key_id=None):
        self.ssm = get_boto3_session().client('ssm')
        self._defaults(kms_key_id=kms_key_id)
        self._key = None
        # 2020-01-27 rrollins: This is weird, since name is a @property here. But I think it maybe works because of how
        # we subclass this class?
        self.name = name

    def _defaults(self, kms_key_id=None):
        # CPM: Should we be checking for proper key format here?
        self.kms_key_id = kms_key_id
        self._value = None
        self._is_secure = False
        self._prefix = ''
        self._aws_parameter = {}

    @property
    def prefix(self):
        return self._prefix

    @property
    def name(self):
        """
        Return the full name of the parameter as we will store it in AWS.

        :rtype: string
        """
        return self.prefix + self.key

    @property
    def value(self):
        """
        Return the value of the parameter as it is in AWS.

        :rtype: string
        """
        if not self._value:
            if self._aws_parameter:
                self._value = self._aws_parameter['Value']
        return self._value

    @property
    def aws_value(self):
        if self._aws_parameter:
            return self._aws_parameter['Value']
        else:
            raise ValueError

    @property
    def key(self):
        """
        Return the parameter name stripped of its prefix.

        :rtype: string
        """
        return self._key

    @property
    def is_secure(self):
        """
        Return ``True`` if we want the value for this parameter to be encrypted
        in AWS, or if we've set a KMS Key ID for it.

        :rtype: boolean
        """
        if self._aws_parameter:
            self._is_secure = self._aws_parameter['Type'] == "SecureString"
        if self.kms_key_id:
            self._is_secure = True
        return self._is_secure

    @property
    def exists(self):
        """
        Return ``True`` if the parameter exists in AWS, ``False`` otherwise.

        :rtype: boolean
        """
        return self._aws_parameter != {}

    def _render_read(self):
        """
        Create an list of keyword parameters suitable for passing to
        ``boto3.client('ssm').get_parameters()``.

        :rtype: dict
        """
        return {
            'Names': [self.name],
            'WithDecryption': True
        }

    def _from_aws(self):
        """
        Set the value of ``self._aws_parameter`` to the data for that parameter from AWS, if
        that parameter exists in AWS, otherwise set ``self._aws_parameter`` to ``{}``
        """
        self._aws_parameter = {}
        response = self.ssm.get_parameters(**self._render_read())
        if response['Parameters']:
            self._aws_parameter = response['Parameters'][0]

    def _render_write(self):
        """
        Create an list of keyword parameters suitable for passing to
        ``boto3.client('ssm').put_parameter()``.

        :rtype: dict
        """
        d = {
            'Name': self.name,
            'Value': self.value,
            'Overwrite': True
        }
        if self.is_secure:
            d['Type'] = 'SecureString'
            if self.kms_key_id:
                d['KeyId'] = self.kms_key_id
        else:
            d['Type'] = 'String'
        return d

    def save(self, overwrite=False):
        """
        Save this parameter to AWS.  If ``overwrite`` is False, raise an exception
        """
        if self.exists and not overwrite:
            raise ValueError('{} exists in AWS: not overwriting'.format(self.name))
        self.ssm.put_parameter(**self._render_write())
        self._from_aws()

    def display(self, key, value):
        """
        Return a human readable display of the key value pair
        :param key:
        :param value:
        :return: string
        """
        base = "{}: {}".format(key, value)
        if self.is_secure:
            base += " [SECURE:{}]".format(self.kms_key_id)
        return base

    def __str__(self):
        return self.display(self.name, self.value)

    # This is the python2 version of the below magic methods for comparison.
    def __cmp__(self, other):
        # cmp is no longer defined in Python 3.
        return cmp(self.name, other.name)  # noqa F821

    def __lt__(self, other):
        return self.name < other.name

    def __gt__(self, other):
        return self.name > other.name

    def __ge__(self, other):
        return self.name >= other.name

    def __le__(self, other):
        return self.name <= other.name

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return self.name != other.name


class UnboundParameter(BaseParameter):
    """
    This is a parameter not bound to an ECS service or task.
    """

    @BaseParameter.prefix.setter
    def prefix(self, value):
        self._prefix = value
        if self._prefix is None:
            self._prefix = ''
        self._from_aws()

    @BaseParameter.name.setter
    def name(self, name):
        if not name:
            raise ValueError('UnboundParameter.name cannot be empty.')
        self._key = name.split('.')[-1]
        prefix = '.'.join(name.split('.')[:-1])
        self._prefix = '{}.'.format(prefix) if prefix else ''
        self._from_aws()

    @BaseParameter.value.setter
    def value(self, new_value):
        self._value = new_value

    @BaseParameter.key.setter
    def key(self, value):
        """
        Set the prefix-free parameter name.

        :param value: string
        """
        if not value:
            raise ValueError('UnboundParameter.key cannot be empty.')
        self._key = value
        self._from_aws()

    def display(self, key, value):
        """
        Return a human readable display of the key value pair
        :param key:
        :param value:
        :return: string
        """
        base = super(UnboundParameter, self).display(key, value)
        if not self._aws_parameter:
            base += " [NOT IN AWS]"
        return base


class ClusterServicePrefixMixin(object):

    @property
    def prefix(self):
        # noinspection PyUnresolvedReferences
        return "{}.{}.".format(self.cluster, self.service)


class Parameter(ClusterServicePrefixMixin, BaseParameter):
    """
    This class represents a parameter in the AWS Systems Manager Parameter Store.
    """

    # noinspection PyMissingConstructor
    def __init__(self, service, cluster, aws=None, yml=None):
        if aws is None:
            aws = {}
        self.ssm = get_boto3_session().client('ssm')
        self.service = service
        self.cluster = cluster
        self._defaults()
        self.is_external = False
        self.__from_yml(yml)
        self._from_aws(aws)

    def _defaults(self, kms_key_id=None):
        super(Parameter, self)._defaults(kms_key_id)
        self._key = None

    @property
    def name(self):
        if self.is_external:
            return self._key
        else:
            return super(Parameter, self).name

    @property
    def key(self):
        """
        Return the parameter key as it is in AWS.

        :rtype: string
        """
        if not self._key:
            if self._aws_parameter:
                self._key = self._aws_parameter['Name'][len(self.prefix):]

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
            if self._aws_parameter:
                self._is_secure = self._aws_parameter['Type'] == "SecureString"
        return self._is_secure

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
        if not self._aws_parameter:
            return True
        else:
            return self.value != self._aws_parameter['Value']

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

    def _from_aws(self, aws=None):
        """
        Return the current value of the parameter named by ``self.key`` as it
        exists in AWS.  If such a parameter does not exist, raise ``KeyError``.
        """
        self._aws_parameter = aws
        if not aws:
            super(Parameter, self)._from_aws()

    def save(self, overwrite=False):
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
        base = super(Parameter, self).display(key, value)
        if self.is_external:
            base += " [EXTERNAL]"
        return base

    def __str__(self):
        return self.display(self.key, self.value)


class UnboundParameterFactory(object):

    @staticmethod
    def new(name):
        """
        Returns a list of UnboundParameters matching ``name``.  If ``name`` ends with "*",
        this could be a long list of parameters.  If there is no "*" in name, there
        will be just one Parameter in the list.

        :param name: the name to search for in AWS SSM Parameter Store

        :return: list of Parameter objects
        """
        m = WILDCARD_RE.search(name)
        if m:
            # This is a wildcard search
            filter_option = "BeginsWith"
            filter_values = [m.group('prefix')]
        else:
            # Get a single parameter
            filter_option = "Equals"
            filter_values = [name]

        ssm = get_boto3_session().client('ssm')
        paginator = ssm.get_paginator('describe_parameters')
        response_iterator = paginator.paginate(
            ParameterFilters=[{
                'Key': 'Name',
                'Option': filter_option,
                'Values': filter_values
            }],
            PaginationConfig={
                'MaxItems': 100,
                'PageSize': 50
            }
        )
        parms = []
        for r in response_iterator:
            parms.extend(r['Parameters'])
        return [UnboundParameter(parm['Name'], kms_key_id=parm.get('KeyId', None) or None) for parm in parms]


class ParameterFactory(object):

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
            m = WILDCARD_RE.search(yml)
            if m:
                parameter_list = []
                ssm = get_boto3_session().client('ssm')
                paginator = ssm.get_paginator('describe_parameters')
                response_iterator = paginator.paginate(
                    ParameterFilters=[{
                        'Key': 'Name',
                        'Option': 'BeginsWith',
                        'Values': [m.group('prefix')]
                    }],
                    PaginationConfig={'MaxItems': 100, 'PageSize': 50}
                )
                parms = []
                for r in response_iterator:
                    parms.extend(r['Parameters'])
                for parm in parms:
                    if parm['Type'] == 'SecureString':
                        line = "{}:external:secure:{}".format(parm['Name'], parm['KeyId'])
                    else:
                        line = "{}:external".format(parm['Name'])
                    parameter_list.append(Parameter(service, cluster, yml=line))
                return parameter_list

        return [Parameter(service, cluster, yml=yml)]


class ParameterStore(ClusterServicePrefixMixin, list):

    """
    This class is the access point for parameters in the AWS System Manager Parameter Store.
    """

    def __init__(self, service, cluster, yml=None):
        super(ParameterStore, self).__init__()
        if yml is None:
            yml = []
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

        self.ssm = get_boto3_session().client('ssm')
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
                    'Values': [self.prefix]
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
