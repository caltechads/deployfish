"""Service discovery manager create/update/list/save coverage."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from deployfish.core.models.service_discovery import (
    ServiceDiscoveryNamespace,
    ServiceDiscoveryService,
)


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


NS_DATA = {
    "Id": "ns-abc123",
    "Arn": "arn:aws:servicediscovery:us-west-2:123:namespace/ns-abc123",
    "Name": "local.internal",
    "Type": "DNS_PRIVATE",
    "CreateDate": "2025-01-01",
    "CreateRequestorId": "creator",
}

SERVICE_DATA = {
    "Id": "srv-hex123",
    "Arn": "arn:aws:servicediscovery:us-west-2:123:service/srv-hex123",
    "Name": "api",
    "NamespaceId": "ns-abc123",
    "Description": "API",
    "CreateDate": "2025-01-01",
    "CreateRequestorId": "creator",
    "DNSConfig": {
        "NamespaceId": "ns-abc123",
        "RoutingPolicy": "MULTIVALUE",
        "DnsRecords": [{"Type": "A", "TTL": 60}],
    },
}


class TestServiceDiscoveryServiceManagerPush:
    def test_list_with_namespace_id_sets_namespace_on_services(
        self, _mock_boto3_session: MagicMock
    ) -> None:
        client = _mock_boto3_session
        namespace = ServiceDiscoveryNamespace(NS_DATA)
        _paginate(client, [{"Services": [SERVICE_DATA]}])
        services = ServiceDiscoveryService.objects.list(namespace=namespace)
        assert services[0].data["NamespaceId"] == "ns-abc123"

    def test_list_resolves_namespace_pk_string(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        namespace = ServiceDiscoveryNamespace(NS_DATA)
        _paginate(client, [{"Services": [SERVICE_DATA]}])
        with patch.object(
            ServiceDiscoveryNamespace.objects, "get", return_value=namespace
        ) as get_mock:
            services = ServiceDiscoveryService.objects.list(namespace="ns-abc123")
        get_mock.assert_called_once_with("ns-abc123")
        assert len(services) == 1

    def test_get_by_namespace_and_name_missing_raises(self) -> None:
        namespace = ServiceDiscoveryNamespace(NS_DATA)
        with (
            patch.object(ServiceDiscoveryNamespace.objects, "get", return_value=namespace),
            patch.object(ServiceDiscoveryService.objects, "list", return_value=[]),
        ):
            with pytest.raises(ServiceDiscoveryService.DoesNotExist):
                ServiceDiscoveryService.objects.get("ns-abc123:missing")

    def test_get_bare_name_not_found_raises(self) -> None:
        with patch.object(ServiceDiscoveryService.objects, "list", return_value=[]):
            with pytest.raises(ServiceDiscoveryService.DoesNotExist):
                ServiceDiscoveryService.objects.get("missing-api")

    def _stub_client_exceptions(self, client: MagicMock) -> None:
        for name in ("NamespaceNotFound", "ServiceNotFound", "ResourceInUse"):
            setattr(client.exceptions, name, type(name, (Exception,), {}))

    def test_create_and_update_return_arn(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        self._stub_client_exceptions(client)
        arn = SERVICE_DATA["Arn"]
        client.create_service.return_value = {"Services": [{"Arn": arn}]}
        client.update_service.return_value = {"Services": [{"Arn": arn}]}
        service = ServiceDiscoveryService(SERVICE_DATA)
        assert ServiceDiscoveryService.objects.create(service) == arn
        assert ServiceDiscoveryService.objects.update(service) == arn

    def test_create_raises_namespace_not_found(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        self._stub_client_exceptions(client)
        service = ServiceDiscoveryService(
            {
                "Id": "srv-new",
                "Arn": "arn:aws:servicediscovery:us-west-2:123:service/srv-new",
                "Name": "api",
                "CreateDate": "2025-01-01",
                "CreateRequestorId": "creator",
                "DNSConfig": {
                    "RoutingPolicy": "MULTIVALUE",
                    "DnsRecords": [{"Type": "A", "TTL": 60}],
                },
            },
            namespace_name="gone.internal",
        )
        client.create_service.side_effect = client.exceptions.NamespaceNotFound("missing")
        with pytest.raises(ServiceDiscoveryService.NamespaceNotFound):
            ServiceDiscoveryService.objects.create(service)

    def test_update_raises_service_not_found(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        self._stub_client_exceptions(client)
        client.update_service.side_effect = client.exceptions.ServiceNotFound("gone")
        service = ServiceDiscoveryService(SERVICE_DATA)
        with pytest.raises(ServiceDiscoveryService.DoesNotExist):
            ServiceDiscoveryService.objects.update(service)

    def test_save_routes_to_create_or_update(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        self._stub_client_exceptions(client)
        arn = SERVICE_DATA["Arn"]
        client.create_service.return_value = {"Services": [{"Arn": arn}]}
        client.update_service.return_value = {"Services": [{"Arn": arn}]}
        service = ServiceDiscoveryService(SERVICE_DATA)
        with patch.object(ServiceDiscoveryService.objects, "exists", return_value=False):
            assert ServiceDiscoveryService.objects.save(service) == arn
        with patch.object(ServiceDiscoveryService.objects, "exists", return_value=True):
            assert ServiceDiscoveryService.objects.save(service) == arn

    def test_delete_raises_resource_in_use(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        self._stub_client_exceptions(client)
        client.delete_service.side_effect = client.exceptions.ResourceInUse("busy")
        service = ServiceDiscoveryService(SERVICE_DATA)
        with pytest.raises(ServiceDiscoveryService.OperationFailed):
            ServiceDiscoveryService.objects.delete(service)


class TestServiceDiscoveryServiceModelPush:
    def test_render_for_update_includes_description(self) -> None:
        service = ServiceDiscoveryService(SERVICE_DATA)
        payload = service.render_for_update()
        assert payload["Id"] == "srv-hex123"
        assert payload["Service"]["Description"] == "API"

    def test_save_assigns_namespace_and_calls_manager(self) -> None:
        service = ServiceDiscoveryService(
            {
                "Name": "api",
                "DnsConfig": {
                    "RoutingPolicy": "MULTIVALUE",
                    "DnsRecords": [{"Type": "A", "TTL": 60}],
                },
            },
            namespace_name="local.internal",
        )
        namespace = ServiceDiscoveryNamespace(NS_DATA)
        with (
            patch.object(
                ServiceDiscoveryService,
                "namespace",
                new_callable=PropertyMock,
                return_value=namespace,
            ),
            patch.object(ServiceDiscoveryService.objects, "save", return_value=SERVICE_DATA["Arn"]) as save_mock,
        ):
            assert service.save() == SERVICE_DATA["Arn"]
        save_mock.assert_called_once()
        assert service.data["NamespaceId"] == "ns-abc123"
        assert service.data["DnsConfig"]["NamespaceId"] == "ns-abc123"

    def test_save_raises_without_namespace(self) -> None:
        service = ServiceDiscoveryService(
            {
                "Name": "api",
                "DNSConfig": {"RoutingPolicy": "MULTIVALUE", "DnsRecords": []},
            }
        )
        with patch.object(
            ServiceDiscoveryService, "namespace", new_callable=PropertyMock, return_value=None
        ):
            with pytest.raises(ServiceDiscoveryService.ImproperlyConfigured):
                service.save()

    def test_namespace_property_caches_miss(self, _mock_boto3_session: MagicMock) -> None:
        exc = type("NamespaceNotFound", (Exception,), {})
        _mock_boto3_session.exceptions.NamespaceNotFound = exc
        _mock_boto3_session.get_namespace.side_effect = exc("missing")
        service = ServiceDiscoveryService({**SERVICE_DATA, "NamespaceId": "ns-gone"})
        assert service.namespace is None
        assert service.cache["namespace"] is None
