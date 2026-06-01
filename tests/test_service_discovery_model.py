from unittest.mock import MagicMock

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
}

SERVICE_DATA = {
    "Id": "srv-hex123",
    "Arn": "arn:aws:servicediscovery:us-west-2:123:service/srv-hex123",
    "Name": "api",
    "NamespaceId": "ns-abc123",
}


class TestServiceDiscoveryNamespaceManager:
    def test_get_by_id(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.get_namespace.return_value = {"Namespace": NS_DATA}
        namespace = ServiceDiscoveryNamespace.objects.get("ns-abc123")
        assert namespace.name == "local.internal"

    def test_get_by_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Namespaces": [NS_DATA]}])
        namespace = ServiceDiscoveryNamespace.objects.get("local.internal")
        assert namespace.pk == "ns-abc123"

    def test_list_private_only(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Namespaces": [NS_DATA]}])
        namespaces = ServiceDiscoveryNamespace.objects.list(private_only=True)
        assert len(namespaces) == 1


class TestServiceDiscoveryServiceManager:
    def test_get_by_service_id(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.get_service.return_value = {"Namespace": SERVICE_DATA}
        service = ServiceDiscoveryService.objects.get("srv-hex123")
        assert service.name == "api"

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        exc = type("ServiceNotFound", (Exception,), {})
        client.exceptions.ServiceNotFound = exc
        client.get_service.side_effect = exc("missing")
        with pytest.raises(ServiceDiscoveryService.DoesNotExist):
            ServiceDiscoveryService.objects.get("srv-missing")
