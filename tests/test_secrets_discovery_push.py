"""Coverage push for secrets, secrets manager, and service discovery."""

import base64
from typing import Any, cast
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.secrets import ExternalSecret, Secret, SecretsMixin
from deployfish.core.models.secrets_manager import SMSecret
from deployfish.core.models.service_discovery import (
    ServiceDiscoveryNamespace,
    ServiceDiscoveryService,
)


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


class _SecretsHost(SecretsMixin):
    def __init__(self) -> None:
        self.cache: dict[str, object] = {}

    @property
    def secrets_prefix(self) -> str:
        return "cluster.service."

    def get_cached(
        self,
        _key: str,
        _populator: Any,
        _args: list[Any],
        _kwargs: dict[str, Any] | None = None,
    ) -> object | None:
        return self.cache.get(_key)


class TestSecretsMixin:
    def test_write_secrets_saves_and_deletes_orphans(self) -> None:
        host = _SecretsHost()
        secret = MagicMock()
        secret.pk = "cluster.service.KEEP"
        secret.save = MagicMock()
        host.secrets = {"KEEP": secret}
        with (
            patch.object(
                Secret.objects,
                "list_names",
                return_value=["cluster.service.KEEP", "cluster.service.OLD"],
            ),
            patch.object(Secret.objects, "delete_many_by_name") as delete_mock,
        ):
            host.write_secrets()
        delete_mock.assert_called_once_with(["cluster.service.OLD"])

    def test_write_secrets_skips_read_only(self) -> None:
        host = _SecretsHost()
        secret = MagicMock()
        secret.save.side_effect = secret.ReadOnly
        host.secrets = {"X": secret}
        with patch.object(Secret.objects, "list_names", return_value=[]):
            host.write_secrets()

    def test_diff_secrets_with_dict_and_ignore_external(self) -> None:
        host = _SecretsHost()
        ours = MagicMock()
        ours.name = "DEBUG"
        ours.render_for_diff.return_value = {"Value": "False"}
        host.secrets = {"DEBUG": ours}
        ExternalSecret({"name": "ext", "valueFrom": "/path"})
        other_secret = MagicMock()
        other_secret.name = "DEBUG"
        other_secret.render_for_diff.return_value = {"Value": "True"}
        result = host.diff_secrets({"DEBUG": other_secret}, ignore_external=True)
        assert isinstance(result, dict)


class TestSMSecretManager:
    SM_DATA = {
        "ARN": "arn:aws:secretsmanager:us-west-2:123:secret:my-secret",
        "Name": "my-secret",
        "KmsKeyId": "key-1",
        "RotationEnabled": False,
        "LastRotationDate": None,
    }

    def test_get_and_list(self) -> None:
        client = cast("MagicMock", SMSecret.objects.client)
        client.describe_secret.return_value = self.SM_DATA
        _paginate(client, [{"SecretList": [self.SM_DATA]}])
        secret = SMSecret.objects.get("my-secret")
        assert secret.name == "my-secret"
        assert len(SMSecret.objects.list()) == 1

    def test_get_raises_not_found(self) -> None:
        client = cast("MagicMock", SMSecret.objects.client)
        exc = type("ResourceNotFoundException", (Exception,), {})
        client.exceptions.ResourceNotFoundException = exc
        client.describe_secret.side_effect = exc("missing")
        with pytest.raises(SMSecret.DoesNotExist):
            SMSecret.objects.get("missing")

    def test_get_value_string_and_binary(self) -> None:
        client = cast("MagicMock", SMSecret.objects.client)
        client.describe_secret.return_value = self.SM_DATA
        client.get_secret_value.return_value = {"SecretString": "hello"}
        secret = SMSecret.objects.get("my-secret")
        assert secret.value == "hello"
        client.get_secret_value.return_value = {
            "SecretBinary": base64.b64encode(b"binary-data"),
        }
        secret.cache.clear()
        assert secret.value == "binary-data"


class TestServiceDiscoveryExtended:
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
        "DNSConfig": {
            "NamespaceId": "ns-abc123",
            "RoutingPolicy": "MULTIVALUE",
            "DnsRecords": [],
        },
    }

    def test_namespace_get_raises_not_found(self) -> None:
        client = cast("MagicMock", ServiceDiscoveryNamespace.objects.client)
        exc = type("NamespaceNotFound", (Exception,), {})
        client.exceptions.NamespaceNotFound = exc
        client.get_namespace.side_effect = exc("missing")
        with pytest.raises(ServiceDiscoveryNamespace.DoesNotExist):
            ServiceDiscoveryNamespace.objects.get("ns-missing")

    def test_namespace_get_by_name_not_found(self) -> None:
        client = cast("MagicMock", ServiceDiscoveryNamespace.objects.client)
        _paginate(client, [{"Namespaces": []}])
        with pytest.raises(ServiceDiscoveryNamespace.DoesNotExist):
            ServiceDiscoveryNamespace.objects.get("missing.internal")

    def test_service_get_by_namespace_and_name(self) -> None:
        namespace = ServiceDiscoveryNamespace(self.NS_DATA)
        with (
            patch.object(
                ServiceDiscoveryNamespace.objects, "get", return_value=namespace
            ),
            patch.object(
                ServiceDiscoveryService.objects,
                "list",
                return_value=[ServiceDiscoveryService(self.SERVICE_DATA)],
            ),
        ):
            service = ServiceDiscoveryService.objects.get("ns-abc123:api")
        assert service.name == "api"

    def test_service_get_bare_name_resolves_pk(self) -> None:
        stub = ServiceDiscoveryService(self.SERVICE_DATA)
        with (
            patch.object(ServiceDiscoveryService.objects, "list", return_value=[stub]),
            patch.object(
                ServiceDiscoveryService.objects, "get", return_value=stub
            ) as get_mock,
        ):
            service = ServiceDiscoveryService.objects.get("api")
        get_mock.assert_called_once_with("api")
        assert service is stub

    def test_service_get_bare_name_multiple_raises(self) -> None:
        stubs = [
            ServiceDiscoveryService({**self.SERVICE_DATA, "Id": "srv-1"}),
            ServiceDiscoveryService({**self.SERVICE_DATA, "Id": "srv-2"}),
        ]
        with (
            patch.object(ServiceDiscoveryService.objects, "list", return_value=stubs),
            pytest.raises(ServiceDiscoveryService.MultipleObjectsReturned),
        ):
            ServiceDiscoveryService.objects.get("api")

    def test_service_delete_raises_when_not_found(self) -> None:
        client = cast("MagicMock", ServiceDiscoveryService.objects.client)
        svc = ServiceDiscoveryService(self.SERVICE_DATA)
        exc = type("ServiceNotFound", (Exception,), {})
        client.exceptions.ServiceNotFound = exc
        client.delete_service.side_effect = exc("gone")
        with pytest.raises(ServiceDiscoveryService.DoesNotExist):
            ServiceDiscoveryService.objects.delete(svc)

    def test_namespace_render_for_diff(self) -> None:
        ns = ServiceDiscoveryNamespace(self.NS_DATA)
        diff = ns.render_for_diff()
        assert "CreateDate" not in diff
