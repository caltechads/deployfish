from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.plugins.postgres.models.postgres import (
    PostgresDatabase,
    _raise_if_binary_missing,
)

DEFAULT_POSTGRES_PORT = 5432
ALTERNATE_POSTGRES_PORT = 5433


def _db(**overrides):
    data = {
        "name": "test",
        "service": "svc",
        "host": "myhost.example.com",
        "db": "mydb",
        "user": "myuser",
        "pass": "mypass",
    }
    data.update(overrides)
    return PostgresDatabase.new(data, "deployfish")


class TestPostgresDatabaseProperties:
    def test_port_defaults_to_5432(self) -> None:
        assert _db().port == DEFAULT_POSTGRES_PORT

    def test_character_set_defaults_to_utf8(self) -> None:
        assert _db().character_set == "UTF8"

    def test_explicit_port_and_character_set(self) -> None:
        db = _db(port=ALTERNATE_POSTGRES_PORT, character_set="LATIN1")
        assert db.port == ALTERNATE_POSTGRES_PORT
        assert db.character_set == "LATIN1"

    def test_config_key_interpolation(self) -> None:
        db = _db(host="config.DB_HOST")
        with patch.object(PostgresDatabase, "secret") as mock_secret:
            mock_secret.return_value = SimpleNamespace(value="10.0.0.5")
            assert db.host == "10.0.0.5"
            mock_secret.assert_called_once_with("DB_HOST")


class TestPostgresDatabaseRenderMethods:
    def test_render_for_create_is_two_chained_invocations(self) -> None:
        db = _db()
        cmd = db.render_for_create("root", "rootpass")
        assert cmd == (
            "PGPASSWORD='rootpass' psql --host=myhost.example.com --username=root "
            "--port=5432 --dbname=postgres "
            "--command=\"CREATE ROLE myuser LOGIN PASSWORD 'mypass';\" && "
            "PGPASSWORD='rootpass' psql --host=myhost.example.com --username=root "
            "--port=5432 --dbname=postgres "
            "--command=\"CREATE DATABASE mydb OWNER myuser ENCODING 'UTF8';\""
        )

    def test_render_for_update(self) -> None:
        db = _db()
        cmd = db.render_for_update("root", "rootpass")
        assert cmd == (
            'PGPASSWORD=\'rootpass\' psql --host=myhost.example.com --username=root '
            '--port=5432 --dbname=postgres --command="ALTER ROLE myuser WITH '
            'PASSWORD \'mypass\';GRANT ALL PRIVILEGES ON DATABASE mydb TO myuser;'
            'GRANT ALL ON SCHEMA public TO myuser;"'
        )

    def test_render_for_validate(self) -> None:
        db = _db()
        assert db.render_for_validate() == (
            "PGPASSWORD='mypass' psql --host=myhost.example.com --username=myuser "
            "--port=5432 --dbname=postgres --tuples-only --no-align "
            '--command="select version(), current_date;"'
        )

    def test_render_for_server_version(self) -> None:
        db = _db()
        assert db.render_for_server_version() == (
            "PGPASSWORD='mypass' psql --host=myhost.example.com --username=myuser "
            "--port=5432 --dbname=postgres --tuples-only --no-align "
            '--command="select version();"'
        )

    def test_render_for_show_grants(self) -> None:
        db = _db()
        assert db.render_for_show_grants() == (
            "PGPASSWORD='mypass' psql --host=myhost.example.com --username=myuser "
            r'--port=5432 --dbname=postgres --command="\du+ myuser"'
        )

    def test_render_for_dump(self) -> None:
        db = _db()
        assert db.render_for_dump() == (
            "PGPASSWORD='mypass' pg_dump --format=plain --no-owner "
            "--host=myhost.example.com --username=myuser --port=5432 --dbname=mydb"
        )

    def test_render_for_load(self) -> None:
        db = _db()
        assert db.render_for_load() == (
            "PGPASSWORD='mypass' psql --host=myhost.example.com --username=myuser "
            "--port=5432 --dbname=mydb --file={filename} && rm {filename}"
        )


class TestRaiseIfBinaryMissing:
    def test_bash_command_not_found_raises(self) -> None:
        db = _db()
        with pytest.raises(db.OperationFailed, match="psql"):
            _raise_if_binary_missing(db, "psql", "bash: psql: command not found\n")

    def test_dash_not_found_raises(self) -> None:
        db = _db()
        with pytest.raises(db.OperationFailed, match="pg_dump"):
            _raise_if_binary_missing(db, "pg_dump", "sh: 1: pg_dump: not found\n")

    def test_normal_failure_does_not_raise(self) -> None:
        db = _db()
        _raise_if_binary_missing(
            db,
            "psql",
            'psql: error: FATAL:  password authentication failed for user "myuser"\n',
        )


class TestPostgresDatabaseManagerMethods:
    def test_create_with_binary_missing_error(self) -> None:
        """Test create() raises when psql is missing."""
        db = _db()
        mock_cluster = SimpleNamespace(
            ssh_noninteractive=lambda *_, **__: (
                False,
                "bash: psql: command not found\n",
            )
        )
        with patch.object(
            PostgresDatabase,
            "cluster",
            new_callable=PropertyMock,
            return_value=mock_cluster,
        ), pytest.raises(db.OperationFailed, match=r"psql.*was not found"):
            db.create("root", "rootpass")

    def test_validate_with_binary_missing_error(self) -> None:
        """Test validate() raises when psql is missing."""
        db = _db()
        mock_cluster = SimpleNamespace(
            ssh_noninteractive=lambda *_, **__: (
                False,
                "sh: 1: psql: not found\n",
            )
        )
        with patch.object(
            PostgresDatabase,
            "cluster",
            new_callable=PropertyMock,
            return_value=mock_cluster,
        ), pytest.raises(db.OperationFailed, match=r"psql.*was not found"):
            db.validate()

    def test_server_version_with_binary_missing_error(self) -> None:
        """Test server_version() raises when psql is missing."""
        db = _db()
        mock_cluster = SimpleNamespace(
            ssh_noninteractive=lambda *_, **__: (
                False,
                "bash: psql: command not found\n",
            )
        )
        with patch.object(
            PostgresDatabase,
            "cluster",
            new_callable=PropertyMock,
            return_value=mock_cluster,
        ), pytest.raises(db.OperationFailed, match=r"psql.*was not found"):
            db.server_version()

    def test_create_with_other_error_not_binary_missing(self) -> None:
        """Test create() raises OperationFailed for non-binary-missing errors."""
        db = _db()
        error_msg = (
            'psql: error: FATAL:  password authentication failed for '
            'user "root"\n'
        )
        mock_cluster = SimpleNamespace(
            ssh_noninteractive=lambda *_, **__: (False, error_msg)
        )
        with patch.object(
            PostgresDatabase,
            "cluster",
            new_callable=PropertyMock,
            return_value=mock_cluster,
        ), pytest.raises(db.OperationFailed, match="Failed to create database"):
            db.create("root", "wrongpass")


class TestPostgresDatabaseAdapterRegistration:
    def test_adapter_is_registered(self) -> None:
        import deployfish.plugins.postgres.adapters  # noqa: F401
        from deployfish.registry import importer_registry

        adapter_cls = importer_registry.get("PostgresDatabase", "deployfish")
        assert adapter_cls.__name__ == "PostgresDatabaseAdapter"
