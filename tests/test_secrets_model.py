from unittest.mock import patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.secrets import Secret, SecretsMixin


class _SecretsHost(SecretsMixin):
    def __init__(self, secrets: dict[str, Secret]) -> None:
        self.cache: dict = {"secrets": secrets}

    @property
    def secrets_prefix(self) -> str:
        return "cluster.service."


class TestSecretModel:
    def test_new_plain_secret(self) -> None:
        secret = Secret.new(
            {"value": "DEBUG=False"}, "deployfish", cluster="c", name="s"
        )
        assert secret.secret_name == "DEBUG"
        assert secret.value == "False"
        assert secret.is_secure is False

    def test_new_secure_secret(self) -> None:
        secret = Secret.new(
            {"value": "DB_PASSWORD:secure:arn:aws:kms:us-west-2:111:key/abc=secret"},
            "deployfish",
            cluster="c",
            name="s",
        )
        assert secret.is_secure is True
        assert secret.data["Type"] == "SecureString"

    def test_save_calls_ssm_put_parameter(self) -> None:
        secret = Secret.new(
            {"value": "DEBUG=False"}, "deployfish", cluster="c", name="s"
        )
        with patch.object(Secret.objects, "save", return_value=1) as save_mock:
            version = secret.save()
        save_mock.assert_called_once_with(secret)
        assert version == 1


class TestSecretsMixinWriteSecrets:
    def test_write_secrets_saves_each_secret(self) -> None:
        secret = Secret.new(
            {"value": "DEBUG=False"}, "deployfish", cluster="c", name="s"
        )
        host = _SecretsHost({"DEBUG": secret})
        with patch.object(secret, "save") as save_mock:
            with patch.object(Secret.objects, "list_names", return_value=[]):
                host.write_secrets()
        save_mock.assert_called_once()

    def test_write_secrets_prunes_removed_names(self) -> None:
        secret = Secret.new(
            {"value": "DEBUG=False"}, "deployfish", cluster="c", name="s"
        )
        host = _SecretsHost({"DEBUG": secret})
        with (
            patch.object(secret, "save"),
            patch.object(
                Secret.objects,
                "list_names",
                return_value=["cluster.service.OLD"],
            ),
            patch.object(Secret.objects, "delete_many_by_name") as delete_mock,
        ):
            host.write_secrets()
        delete_mock.assert_called_once_with(["cluster.service.OLD"])

    def test_diff_secrets_detects_changes(self) -> None:
        ours = Secret.new({"value": "DEBUG=True"}, "deployfish", cluster="c", name="s")
        theirs = Secret.new(
            {"value": "DEBUG=False"}, "deployfish", cluster="c", name="s"
        )
        theirs.data["Name"] = ours.data["Name"]
        host = _SecretsHost({"DEBUG": ours})
        changes = host.diff_secrets([theirs], ignore_external=True)
        assert changes
