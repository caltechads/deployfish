import deployfish.core.adapters  # noqa: F401
from deployfish.core.adapters.deployfish.secrets import (
    SecretAdapter,
    SecretsMixin,
    parse_secret_string,
)
from deployfish.core.models import Secret


class TestParseSecretString:
    def test_plain_string(self) -> None:
        key, kwargs = parse_secret_string("DEBUG=False")
        assert key == "DEBUG"
        assert kwargs["Value"] == "False"
        assert kwargs["Type"] == "String"
        assert "KeyId" not in kwargs

    def test_secure_string(self) -> None:
        key, kwargs = parse_secret_string("DB_PASSWORD:secure=secret_value")
        assert key == "DB_PASSWORD"
        assert kwargs["Type"] == "SecureString"
        assert kwargs["Value"] == "secret_value"
        assert kwargs["KeyId"] is None

    def test_secure_string_with_kms_arn(self) -> None:
        secret = "DB_PASSWORD:secure:arn:aws:kms:us-west-2:111122223333:key/abc=secret"
        key, kwargs = parse_secret_string(secret)
        assert key == "DB_PASSWORD"
        assert kwargs["Type"] == "SecureString"
        assert kwargs["KeyId"] == "arn:aws:kms:us-west-2:111122223333:key/abc"


class TestSecretAdapter:
    def test_convert_builds_parameter_name(self) -> None:
        adapter = SecretAdapter(
            {"value": "DEBUG=False"},
            cluster="my-cluster",
            name="my-service",
        )
        data, kwargs = adapter.convert()
        assert data["Name"] == "my-cluster.my-service.DEBUG"
        assert data["Type"] == "String"
        assert kwargs["name"] == "DEBUG"

    def test_is_external_detects_external_spec(self) -> None:
        adapter = SecretAdapter({"value": "/path/to/*:external"})
        assert adapter.is_external() is True

    def test_is_external_false_for_normal_spec(self) -> None:
        adapter = SecretAdapter({"value": "DEBUG=False"})
        assert adapter.is_external() is False

    def test_convert_raises_for_external(self) -> None:
        adapter = SecretAdapter({"value": "/path/to/*:external"})
        try:
            adapter.convert()
        except SecretAdapter.ExternalParameterException:
            pass
        else:
            raise AssertionError("expected ExternalParameterException")


class TestSecretsMixinGetSecrets:
    def test_get_secrets_from_config(self) -> None:
        mixin = SecretsMixin()
        mixin.data = {
            "config": [
                "DEBUG=False",
                "DB_HOST=myhost",
            ]
        }
        secrets = mixin.get_secrets("cluster-a", "service-a")
        assert len(secrets) == 2
        assert all(isinstance(s, Secret) for s in secrets)
        assert secrets[0].secret_name == "DEBUG"
        assert secrets[1].secret_name == "DB_HOST"

    def test_get_secrets_empty_when_no_config(self) -> None:
        mixin = SecretsMixin()
        mixin.data = {}
        assert mixin.get_secrets("cluster-a", "service-a") is None
