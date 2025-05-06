from collections.abc import Sequence
from copy import copy
from typing import Any, Union, cast

from .abstract import Manager, Model

# ----------------------------------------
# Managers
# ----------------------------------------


class ServiceDiscoveryNamespaceManager(Manager):

    service = "servicediscovery"

    def get(self, pk: str, **_) -> "ServiceDiscoveryNamespace":
        if pk.startswith("ns-"):
            # this is a namespace['Id']
            try:
                response = self.client.get_namespace(Id=pk)
            except self.client.exceptions.NamespaceNotFound:
                raise ServiceDiscoveryNamespace.DoesNotExist(
                    f'No Service Discovery namespace with id="{pk}" exists in AWS.'
                )
            return ServiceDiscoveryNamespace(response["Namespace"])
        # Assume this is a namespace['Name']
        namespaces = self.list(private_only=True)
        for namespace in namespaces:
            if namespace.name == pk:
                return namespace
        raise ServiceDiscoveryNamespace.DoesNotExist(
            f'No Service Discovery namespace with name="{pk}" exists in AWS.'
        )

    def list(self, private_only: bool = False) -> Sequence["ServiceDiscoveryNamespace"]:
        kwargs = {}
        if private_only:
            kwargs["Filters"] = [{"Name": "TYPE", "Values": ["DNS_PRIVATE"], "Condition": "EQ"}]
        paginator = self.client.get_paginator("list_namespaces")
        response_iterator = paginator.paginate(**kwargs)
        namespaces = []
        for response in response_iterator:
            namespaces.extend(response["Namespaces"])
        return [ServiceDiscoveryNamespace(d) for d in namespaces]


class ServiceDiscoveryServiceManager(Manager):

    service = "servicediscovery"

    def _get_with_id(self, pk: str) -> "ServiceDiscoveryService":
        """
        `pk` is a service['Id']: "srv-{hexstring}"
        """
        try:
            response = self.client.get_service(Id=pk)
        except self.client.exceptions.ServiceNotFound:
            raise ServiceDiscoveryService.DoesNotExist(
                f'No Service Discovery service with id="{pk}" exists in AWS.'
            )
        return ServiceDiscoveryService(response["Namespace"])

    def _get_with_namespace_and_service_name(self, pk: str) -> "ServiceDiscoveryService":
        """
        Pk looks like '{namespace_pk}:{service_name}'
        """
        # this is a namespace_pk:service_name
        namespace_pk, service_name = pk.split(":", 1)
        namespace = ServiceDiscoveryNamespace.objects.get(namespace_pk)
        services = self.list(namespace=namespace)
        for service in services:
            if service.name == service_name:
                return service
        raise ServiceDiscoveryService.DoesNotExist(
            f'No Service Discovery service with name="{pk}" exists in namespace "{namespace_pk}" in AWS.'
        )

    def _get_with_bare_service_name(self, pk: str) -> "ServiceDiscoveryService":
        """
        `pk` is just a bare service name.
        """
        # this is just a bare service name
        services = self.list()
        found = []
        for service in services:
            if service.name == pk:
                found.append(service)
        if len(found) == 0:
            raise ServiceDiscoveryService.DoesNotExist(
                f'No Service Discovery service with name="{pk}" exists in AWS.'
            )
        if len(found) > 1:
            raise ServiceDiscoveryService.MultipleObjectsReturned(
                f'More than one Service Discovery service with name="{pk}" exists in AWS.'
            )
        # We have to do this because the NamespaceId is not included in the services returned by
        # self.client.list_services, but is included in self.client.get_service
        return self.get(found[0].pk)

    def get(self, pk: str, **_) -> "ServiceDiscoveryService":
        """
        `pk` is one of::

            * a service id, which starts with "srv-"
            * a string like '{namespace_pk}:{service_name}'
            * a string like '{service_name}'
        """
        if pk.startswith("srv-"):
            return self._get_with_id(pk)
        if ":" in pk:
            return self._get_with_namespace_and_service_name(pk)
        return self._get_with_bare_service_name(pk)

    def list(self, namespace: Union[str, "ServiceDiscoveryNamespace"] = None) -> Sequence["ServiceDiscoveryService"]:
        kwargs = {}
        if namespace:
            if not isinstance(namespace, ServiceDiscoveryNamespace):
                namespace = ServiceDiscoveryNamespace.objects.get(namespace)
            kwargs["Filters"] = [{"Name": "NAMESPACE_ID", "Values": [namespace.pk], "Condition": "EQ"}]
        namespace = cast("ServiceDiscoveryNamespace", namespace)
        paginator = self.client.get_paginator("list_services")
        response_iterator = paginator.paginate(**kwargs)
        service_defs = []
        for response in response_iterator:
            service_defs.extend(response["Services"])
        services = [ServiceDiscoveryService(d) for d in service_defs]
        if namespace:
            for service in services:
                service.data["NamespaceId"] = namespace.pk
        return services

    def save(self, obj: Model, **_) -> str:
        obj = cast("ServiceDiscoveryService", obj)
        if not self.exists(obj.pk):
            return self.create(obj)
        return self.update(obj)

    def create(self, obj: "ServiceDiscoveryService") -> str:
        try:
            response = self.client.create_service(**obj.render_for_create())
        except self.client.exceptions.NamespaceNotFound:
            raise ServiceDiscoveryService.NamespaceNotFound(
                f'No Service Discovery namespace with name="{obj.namespace_name}" exists in AWS'
            )
        return response["Services"][0]["Arn"]

    def update(self, obj: "ServiceDiscoveryService") -> str:
        try:
            response = self.client.update_service(**obj.render_for_update())
        except self.client.exceptions.ServiceNotFound:
            raise ServiceDiscoveryService.DoesNotExist(
                f'No Service Discovery service with id="{obj.pk}" exists in AWS.'
            )
        return response["Services"][0]["Arn"]

    def delete(self, obj: Model, **_) -> None:
        try:
            self.client.delete_service(obj.pk)
        except self.client.exceptions.ServiceNotFound:
            raise ServiceDiscoveryService.DoesNotExist(
                f'No Service Discovery service with id="{obj.pk}" exists in AWS.'
            )
        except self.client.exceptions.ResourceInUse:
            raise ServiceDiscoveryService.OperationFailed(
                f'Service Discovery service with id="{obj.pk}" cannot be deleted because it is in use.'
            )


# ----------------------------------------
# Models
# ----------------------------------------

class ServiceDiscoveryNamespace(Model):

    objects = ServiceDiscoveryNamespaceManager()

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        return self.data["Id"]

    @property
    def name(self) -> str:
        return self.data["Name"]

    @property
    def arn(self) -> str:
        return self.data["Arn"]

    def render_for_diff(self):
        data = self.render()
        del data["CreateDate"]
        del data["CreateRequestorId"]
        return data


class ServiceDiscoveryService(Model):
    """
    self.data has this structure::

        'Id': 'string',                             [optional]
        'Arn': 'string',                            [optional]
        'Name': 'string',
        'NamespaceId': 'string',                    [optional]
        'Description': 'string',                    [optional]
        'InstanceCount': 123,                       [optional]
        'DnsConfig': {
            'NamespaceId': 'string',
            'RoutingPolicy': 'MULTIVALUE'|'WEIGHTED',
            'DnsRecords': [
                {
                    'Type': 'SRV'|'A'|'AAAA'|'CNAME',
                    'TTL': 123
                },
            ]
        },
        'Type': 'HTTP'|'DNS_HTTP'|'DNS',
        'HealthCheckConfig': {                       [optional]
            'Type': 'HTTP'|'HTTPS'|'TCP',
            'ResourcePath': 'string',
            'FailureThreshold': 123
        },
        'HealthCheckCustomConfig': {                 [optional]
            'FailureThreshold': 123
        },
        'CreateDate': datetime(2015, 1, 1),          [optional]
        'CreatorRequestId': 'string'                 [optional]


    Any key marked as [optional] won't be present if we've loaded this instance from
    deployfish.yml, but may be there if we loaded it from AWS.
    """

    objects = ServiceDiscoveryServiceManager()

    class NamespaceNotFound(Exception):
        """
        The namespace that this service is configured with does not exist in AWS.
        """


    def __init__(self, data: dict[str, Any], **kwargs):
        self.namespace_name: str | None = kwargs.pop("namespace_name", None)
        super().__init__(data, **kwargs)

    # ---------------------
    # Model overrides
    # ---------------------

    @property
    def pk(self) -> str:
        if self.data.get("Id", None):
            return self.data["Id"]
        if self.data.get("NamespaceId", None):
            return f"{self.data['NamespaceId']}:{self.name}"
        if self.namespace_name:
            return f"{self.namespace_name}:{self.name}"
        return self.name

    @property
    def name(self) -> str:
        return self.data["Name"]

    @property
    def arn(self) -> str:
        return self.data["Arn"]

    def render_for_diff(self) -> dict[str, Any]:
        data = self.render()
        del data["Id"]
        del data["Arn"]
        del data["CreateDate"]
        del data["CreateRequestorId"]
        return data

    def render_for_create(self) -> dict[str, Any]:
        return self.render_for_diff()

    def render_for_update(self) -> dict[str, Any]:
        data = {}
        data["Id"] = self.data["Id"]
        service = {}
        if "Description" in self.data:
            service["Description"] = self.data["Description"]
        data["DNSConfig"] = copy(self.data["DNSConfig"])
        if "HealthCheckCOnfig" in self.data:
            service["HealthCheckConfig"] = copy(self.data["HealthCheckConfig"])
        data["Service"] = service
        return data

    def save(self) -> str:
        if not self.namespace:
            raise self.ImproperlyConfigured(
                f'Service Discovery service "{self.name}" has no namespace assigned'
            )
        self.data["NamespaceId"] = self.namespace.pk
        self.data["DnsConfig"]["NamespaceId"] = self.namespace.pk
        return super().save()

    # -------------------------------------------
    # ServiceDiscoveryService-specific properties
    # -------------------------------------------

    @property
    def namespace(self) -> ServiceDiscoveryNamespace | None:
        if "NamespaceId" in self.data:
            pk = self.data["NamespaceId"]
        elif self.namespace_name:
            pk = self.namespace_name
        else:
            self.cache["namespace"] = None
            return None
        try:
            return self.get_cached("namespace", ServiceDiscoveryNamespace.objects.get, [pk])
        except ServiceDiscoveryNamespace.DoesNotExist:
            self.cache["namespace"] = None
            return None
