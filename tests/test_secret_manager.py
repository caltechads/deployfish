from unittest.mock import MagicMock

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.secrets import Secret


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


PARAM_META = {
    "Name": "cluster.service.DEBUG",
    "Type": "String",
    "Tier": "Standard",
}

PARAM_VALUE = {
    "Name": "cluster.service.DEBUG",
    "ARN": "arn:aws:ssm:us-west-2:123:parameter/cluster.service.DEBUG",
    "Value": "False",
    "Type": "String",
}


class TestSecretManager:
    def test_get_parameter(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.get_parameters.return_value = {"Parameters": [PARAM_VALUE], "InvalidParameters": []}
        _paginate(client, [{"Parameters": [PARAM_META]}])
        secret = Secret.objects.get("cluster.service.DEBUG")
        assert secret.value == "False"
        assert secret.secret_name == "DEBUG"

    def test_get_raises_when_missing(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.get_parameters.return_value = {
            "Parameters": [],
            "InvalidParameters": ["cluster.service.MISSING"],
        }
        _paginate(client, [{"Parameters": []}])
        with pytest.raises(Secret.DoesNotExist):
            Secret.objects.get("cluster.service.MISSING")

    def test_list_names_by_prefix(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(
            client,
            [
                {
                    "Parameters": [
                        {"Name": "cluster.service.DEBUG"},
                        {"Name": "cluster.service.DB_HOST"},
                    ]
                }
            ],
        )
        names = Secret.objects.list_names("cluster.service.")
        assert len(names) == 2

    def test_list_returns_secrets(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(client, [{"Parameters": [PARAM_META]}])
        client.get_parameters.return_value = {"Parameters": [PARAM_VALUE], "InvalidParameters": []}
        secrets = Secret.objects.list("cluster.service.")
        assert len(secrets) == 1
        assert secrets[0].secret_name == "DEBUG"

    def test_get_many_batches_over_ten(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        names = [f"cluster.service.KEY{i}" for i in range(11)]
        meta = [{"Name": name, "Type": "String", "Tier": "Standard"} for name in names]
        values = [
            {
                "Name": name,
                "ARN": f"arn:aws:ssm:1:parameter/{name}",
                "Value": "v",
                "Type": "String",
            }
            for name in names
        ]
        _paginate(client, [{"Parameters": meta}])
        client.get_parameters.side_effect = [
            {"Parameters": values[:10], "InvalidParameters": []},
            {"Parameters": values[10:], "InvalidParameters": []},
        ]
        secrets = Secret.objects.get_many(names)
        assert len(secrets) == 11
