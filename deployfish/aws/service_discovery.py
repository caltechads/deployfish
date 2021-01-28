from deployfish.aws import get_boto3_session


class ServiceDiscovery(object):

    """
    This class exists to manage the service discovery configuration on the ECS service.
    Requires that a private dns namespace already exists.
    """

    def __init__(self, registry_arn=None, yml=None):
        """
        ``yml`` is dict parsed from the ``service_discovery`` section from
        ``deployfish.yml``.  Example:

            {
                'namespace': 'local',
                'name': 'test',
                'dns_records': [
                    {
                        'type': 'A',
                        'ttl': '60',
                    }
                ],

        :param yml: service discovery config from ``deployfish.yml`` as described above
        :type yml: dict
        """
        if yml is None:
            yml = {}
        self.sd = get_boto3_session().client('servicediscovery')
        self.__defaults()
        self._registry_arn = registry_arn
        self.from_yaml(yml)

    def __defaults(self):
        self._routing_policy = 'MULTIVALUE'
        self._namespace = None
        self._name = None
        self._namespace_id = None
        self._service_arn = None

    def from_yaml(self, yml):
        """
        Load our configuration from the config read from ``deployfish.yml``.

        :param yml: a service_discovery level entry from the ``deployfish.yml`` file
        :type yml: dict
        """
        if yml:
            self._name = yml['name']
            if 'routing_policy' in yml:
                self._routing_policy = yml['routing_policy']
            self._namespace = yml['namespace']
            self._namespace_id = self.get_namespace(self._namespace)
            self.dns_records = []
            dns = {'Type': yml['dns_records']['type'], 'TTL': yml['dns_records']['ttl']}
            self.dns_records.append(dns)

    def get_namespace(self, name):
        """
        Returns a service discovery namespace id if the namespace exits and
        throws a SystemExit error if it doesn't exist. The namespace id is required
        to setup a new service discovery service.

        :rtype: string
        """
        next_token = ''
        resources = []
        namespace_id = None
        while next_token is not None:
            if next_token == '':
                response = self.sd.list_namespaces(
                    Filters=[
                        {
                            'Name': 'TYPE',
                            'Values': ['DNS_PRIVATE'],
                            'Condition': 'EQ'
                        }
                    ]
                )
            else:
                response = self.sd.list_namespaces(
                    NextToken=next_token,
                    Filters=[
                        {
                            'Name': 'TYPE',
                            'Values': ['DNS_PRIVATE'],
                            'Condition': 'EQ'
                        }
                    ]
                )
            current_batch, next_token = self.get_resources_from(response, 'Namespaces')
            resources += current_batch

        for namespace in resources:
            if namespace['Name'] == name:
                namespace_id = namespace['Id']

        if namespace_id is None:
            print("Service Discovery Namespace doesn't exist!")
            raise SystemExit(1)

        return namespace_id

    def get_resources_from(self, details, index):
        results = details[index]
        next_token = details.get('NextToken', None)
        return results, next_token

    def exists(self):
        """
        Return ``True`` if the service discovery service already exists.

        :rtype: boolean
        """
        next_token = ''
        resources = []
        while next_token is not None:
            if next_token == '':
                response = self.sd.list_services()
            else:
                response = self.sd.list_services(NextToken=next_token)
            current_batch, next_token = self.get_resources_from(response, 'Services')
            resources += current_batch

        for item in resources:
            if self._registry_arn is not None:
                if item['Arn'] == self._registry_arn:
                    self._service_id = item['Id']
                    return True
            else:
                if item['Name'] == self._name:
                    self._service_id = item['Id']
                    return True

        return False

    def __render_create(self):
        return {
            'Name': self._name,
            'DnsConfig': {
               'NamespaceId': self._namespace_id,
               'RoutingPolicy': self._routing_policy,
               'DnsRecords': self.dns_records
            }
        }

    def create(self):
        kwargs = self.__render_create()
        response = self.sd.create_service(**kwargs)
        return response["Service"]["Arn"]

    def delete(self):
        if self.exists():
            self.sd.delete_service(Id=self._service_id)
