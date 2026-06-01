"""SecretManager edge cases."""

from unittest.mock import MagicMock

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.models.secrets import Secret


class TestSecretManagerEdgeCases:
    def test_delete_many_by_name(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        Secret.objects.delete_many_by_name(["a", "b"])
        assert client.delete_parameters.call_count == 1

    def test_save_readonly_manager_raises(self) -> None:
        from deployfish.core.models.secrets import SecretManager

        readonly = SecretManager(Secret, readonly=True)
        secret = Secret({"Name": "cluster.s.DEBUG", "Value": "1", "Type": "String"})
        with pytest.raises(Secret.ReadOnly):
            readonly.save(secret)
