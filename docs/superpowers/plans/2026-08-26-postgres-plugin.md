# Postgres Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `deployfish postgres` cement plugin that exposes the same command set as the existing `deployfish mysql` plugin (`info`, `create`, `update`, `validate`, `dump`, `load`, `show-grants`, `server-version`) for PostgreSQL/RDS Postgres targets.

**Architecture:** A new `deployfish/plugins/postgres/` package mirroring `deployfish/plugins/mysql/`'s cement controller/model/adapter/hooks layout file-for-file. All remote work runs over SSH via the existing `Cluster.ssh_noninteractive()`/`push_file()` machinery, shelling out to bare `psql`/`pg_dump` (resolved off the remote `$PATH`, no hardcoded binary paths). Plugin loading is automatic (cement's built-in `CementPluginHandler` auto-discovers `deployfish/plugins/<name>/` by convention) — no `pyproject.toml` or `main.py` changes anywhere in this plan.

**Tech Stack:** Python, cement (CLI framework), Jinja2 (detail template), pytest (unit tests), `psql`/`pg_dump` (remote CLI tools), PostgreSQL 18.6.

**Spec:** `docs/adr/0003-postgres-plugin.md` — read this ADR in full before starting; this plan implements its decisions exactly, including the two-invocation `create` command (PostgreSQL cannot run `CREATE DATABASE` inside a transaction block, so it must NOT be combined with `CREATE ROLE` in one `psql -c` string).

## Global Constraints

- Target PostgreSQL 18.6 only. No version-branching logic anywhere (no `major_server_version()`, no mysql-style 5.6-vs-8.0 split).
- Config section is `postgres:` in `deployfish.yml`, same shape as `mysql:`: list of dicts with `name`, `service`, `host`, `db`, `user`, `pass` required, `port` (default `5432`) and `character_set` (default `'UTF8'`) optional. No `collation` key. Values may reference `config.KEY` to resolve through the owning service's AWS SSM secrets (identical mechanism to mysql's `parse()`).
- Naming: `PostgresDatabase` (model), `PostgresDatabaseManager` (manager), `PostgresDatabaseAdapter` (adapter), `config_section = "postgres"`, controller `Meta.label = "postgres"`, CLI `deploy postgres <verb>`, config toggle `plugin.postgres: enabled: true`. No `pg`/`psql` abbreviations in any class, section, or command name.
- All remote commands invoke bare `psql`/`pg_dump` (never an absolute path), and auth uses `PGPASSWORD='{password}'` as an env-var prefix (postgres client tools have no `--password=` flag).
- `create`'s two SQL statements (`CREATE ROLE`, `CREATE DATABASE`) MUST be sent as two separate `psql -c` invocations chained with shell `&&`, never combined into one `-c` string — PostgreSQL wraps a multi-statement query-protocol message in an implicit transaction, and `CREATE DATABASE` cannot run inside one.
- Every manager method that shells out to `psql`/`pg_dump` must detect a remote "binary not found" failure and raise a specific, actionable error naming the missing binary, before falling through to the generic `OperationFailed` message.
- No shared base class between the mysql and postgres models — they are independent, parallel plugins.
- Use `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy` per this project's `AGENTS.md`.

---

## File Structure

```
deployfish/plugins/postgres/
├── __init__.py                              # load(app): register controller, hooks, template dir
├── hooks.py                                 # pre_config_interpolate_add_postgres_section
├── models/
│   ├── __init__.py                          # empty
│   └── postgres.py                          # PostgresDatabaseManager, PostgresDatabase, _raise_if_binary_missing
├── adapters/
│   ├── __init__.py                          # from .deployfish import *
│   └── deployfish/
│       ├── __init__.py                      # registry.register("PostgresDatabase", "deployfish", PostgresDatabaseAdapter)
│       └── postgres.py                      # PostgresDatabaseAdapter
├── controllers/
│   ├── __init__.py                          # empty
│   └── postgres.py                          # PostgresController(ReadOnlyCrudBase)
└── templates/
    ├── __init__.py                          # empty
    └── detail--postgresdatabase.jinja2      # info command detail view

docs/source/plugins/postgres.rst             # orphan doc page, mirrors mysql.rst

tests/test_postgres_model.py                 # unit tests: properties, render_for_* builders, binary-check helper
```

---

### Task 1: `PostgresDatabase` model + manager + missing-binary detection

**Files:**
- Create: `deployfish/plugins/postgres/models/__init__.py`
- Create: `deployfish/plugins/postgres/models/postgres.py`
- Test: `tests/test_postgres_model.py`

**Interfaces:**
- Consumes: `deployfish.core.models.{Cluster, Instance, Manager, Model, Secret, Service}` (same imports mysql's model uses), `deployfish.config.get_config()`.
- Produces (used by Task 2 adapter and Task 3 controller):
  - `class PostgresDatabase(Model)` with `config_section = "postgres"`, `objects = PostgresDatabaseManager()`.
  - Properties: `.pk`, `.name`, `.host`, `.user`, `.db`, `.password`, `.character_set` (default `"UTF8"`), `.port` (default `5432`), `.ssh_target`, `.ssh_targets`, `.service` (getter+setter), `.cluster`.
  - Methods: `.secret(name: str) -> Secret`, `.parse(key: str) -> str`, `.create(root_user, root_password, ssh_target=None, verbose=False) -> str`, `.update(root_user, root_password, ssh_target=None, verbose=False) -> str`, `.validate(ssh_target=None, verbose=False) -> str`, `.dump(filename=None, ssh_target=None, verbose=False) -> tuple[str, str]`, `.load(filename, ssh_target=None, verbose=False) -> str`, `.server_version(ssh_target=None, verbose=False, user=None, password=None) -> str`, `.show_grants(ssh_target=None, verbose=False) -> str`.
  - Render methods: `.render_postgres_command(sql, dbname="postgres", user=None, password=None, unaligned=False) -> str`, `.render_for_create(root_user, root_password) -> str`, `.render_for_update(root_user, root_password) -> str`, `.render_for_dump() -> str`, `.render_for_load() -> str`, `.render_for_validate() -> str`, `.render_for_server_version(user=None, password=None) -> str`, `.render_for_show_grants() -> str`.
  - Module-level `_raise_if_binary_missing(obj: "PostgresDatabase", binary: str, output: str) -> None` — raises `obj.OperationFailed(...)` if `output` looks like a shell "command not found" error for `binary`, otherwise returns `None`.
  - `class PostgresDatabaseManager(Manager)` with `.get(pk, **_) -> PostgresDatabase`, `.list(service_name=None, **_) -> Sequence[PostgresDatabase]`, `.save(obj, root_user, root_password, ssh_target=None, verbose=False) -> str` (alias for `.create`), `.create(...)`, `.update(...)`, `.validate(...)`, `.dump(...)`, `.load(...)`, `.server_version(...)`, `.show_grants(...)` — same signatures as `MySQLDatabaseManager`'s equivalents minus `major_server_version`.

- [ ] **Step 1: Write `deployfish/plugins/postgres/models/__init__.py`**

Empty file (matches `deployfish/plugins/mysql/models/__init__.py`).

```python
```

- [ ] **Step 2: Write `deployfish/plugins/postgres/models/postgres.py`**

```python
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from deployfish.config import get_config
from deployfish.core.models import Cluster, Instance, Manager, Model, Secret, Service

# ----------------------------------------
# Helpers
# ----------------------------------------


def _raise_if_binary_missing(obj: "PostgresDatabase", binary: str, output: str) -> None:
    """
    Raise a clear, actionable error if a remote ``psql``/``pg_dump`` command failed
    because the binary itself isn't on the remote host's ``$PATH``, rather than
    because of an authentication, SQL, or permission failure.

    Args:
        obj: the PostgresDatabase we were operating on when the command failed
        binary: the name of the binary we tried to run (e.g. ``"psql"``)
        output: the combined stdout/stderr of the failed remote command

    Raises:
        PostgresDatabase.OperationFailed: if ``output`` looks like a shell
            "command not found" error for ``binary``.

    """
    for line in output.splitlines():
        line = line.strip()
        if binary not in line:
            continue
        if "command not found" in line or ": not found" in line or line.endswith(
            "not found"
        ):
            msg = (
                f'"{binary}" was not found on the remote host\'s $PATH. Install '
                f'the PostgreSQL client tools (which provide "{binary}") on that '
                f"host and try again."
            )
            raise obj.OperationFailed(msg)


# ----------------------------------------
# Managers
# ----------------------------------------


class PostgresDatabaseManager(Manager):
    """
    Model postgres database manager behavior.
    """

    def get(self, pk: str, **_) -> Model:
        """
        Get the PostgresDatabase object from the config file.

        Args:
            pk: the name of the database to get from the config file.

        Raises:
            PostgresDatabase.DoesNotExist: No PostgresDatabase object with that
                name exists in the config file.

        Returns:
            The PostgresDatabase object.

        Keyword Args:
            _: .

        """
        config = get_config()
        section = config.get_section("postgres")
        databases = {}
        for data in section:
            databases[data["name"]] = data
        if pk in databases:
            return PostgresDatabase.new(databases[pk], "deployfish")
        msg = f'Could not find an PostgresDatabase config named "{pk}" in deployfish.yml:postgres'  # noqa: E501
        raise PostgresDatabase.DoesNotExist(msg)

    def list(
        self, service_name: str | None = None, **_
    ) -> Sequence["PostgresDatabase"]:
        """
        List the PostgresDatabase objects in the config file.

        Returns:
            A list of PostgresDatabase objects.

        Args:
            service_name: service name.

        Keyword Args:
            _: .

        """
        config = get_config()
        section = config.get_section("postgres")
        databases = [PostgresDatabase.new(db, "deployfish") for db in section]
        if service_name:
            databases = [db for db in databases if db.data["service"] == service_name]
        return cast("list[PostgresDatabase]", databases)

    def save(  # type: ignore[misc]  # pylint:disable=arguments-differ
        self,
        obj: "PostgresDatabase",
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Is an alias for :py:meth:`create`.

        Args:
            obj: The ``PostgresDatabase`` object
            root_user: The root user to use to connect to the database.
            root_password: The root password to use to connect to the database.

        Keyword Args:
            ssh_target: the ssh instance to use for running our postgres commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The create failed because of some
                unexpected error.

        Returns:
            The output of the create commands.

        """
        return self.create(
            obj, root_user, root_password, ssh_target=ssh_target, verbose=verbose
        )

    def create(
        self,
        obj: "PostgresDatabase",
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Create the role and database for ``obj``.

        Args:
            obj: The ``PostgresDatabase`` object
            root_user: The root user to use to connect to the database.
            root_password: The root password to use to connect to the database.

        Keyword Args:
            ssh_target: the ssh instance to use for running our postgres
                commands.  If not supplied, we will use the ``cluster``'s
                default ssh instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The create failed because of some
                unexpected error.

        Returns:
            The output of the create commands.

        """
        command = obj.render_for_create(root_user, root_password)
        status, output = obj.cluster.ssh_noninteractive(
            command, ssh_target=ssh_target, verbose=verbose
        )
        if status:
            return output
        _raise_if_binary_missing(obj, "psql", output)
        msg = f'Failed to create database "{obj.db}" and/or role "{obj.user}" on {obj.host}:{obj.port}: {output}'  # noqa: E501
        raise obj.OperationFailed(msg)

    def update(
        self,
        obj: "PostgresDatabase",
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Update the password and grants for the database role on ``obj``.

        Args:
            obj: The ``PostgresDatabase`` object
            root_user: The root user to use to connect to the database.
            root_password: The root password to use to connect to the database.

        Keyword Args:
            ssh_target: the ssh instance to use for running our postgres
                commands.  If not supplied, we will use the ``cluster``'s
                default ssh instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The update failed because of some
                unexpected error.

        Returns:
            The output of the update commands.

        """
        command = obj.render_for_update(root_user, root_password)
        success, output = obj.cluster.ssh_noninteractive(
            command, ssh_target=ssh_target, verbose=verbose
        )
        if success:
            return output
        _raise_if_binary_missing(obj, "psql", output)
        msg = f'Failed to update database "{obj.db}" and/or role "{obj.user}" on {obj.host}:{obj.port}: {output}'  # noqa: E501
        raise obj.OperationFailed(msg)

    def validate(
        self, obj: "PostgresDatabase", ssh_target: Instance = None, verbose: bool = False  # noqa: FBT001, FBT002
    ) -> str:
        """
        Validate that the database and role exist on the target Postgres server.

        Args:
            obj: The ``PostgresDatabase`` object to validate.

        Keyword Args:
            ssh_target: the ssh instance to use for running our postgres
                commands.  If not supplied, we will use the ``cluster``'s
                default ssh instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The validation failed because of some
                unexpected error.

        Returns:
            The output of the validation commands.

        """
        command = obj.render_for_validate()
        success, output = obj.cluster.ssh_noninteractive(
            command, ssh_target=ssh_target, verbose=verbose
        )
        if success:
            return output
        _raise_if_binary_missing(obj, "psql", output)
        msg = f'Failed to validate role "{obj.user}" on {obj.host}:{obj.port}: {output}'
        raise obj.OperationFailed(msg)

    def dump(
        self,
        obj: "PostgresDatabase",
        filename: str | None = None,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> tuple[str, str]:
        """
        Use ``pg_dump`` to dump the remote database as SQL to a local file.

        If ``filename`` is not supplied, the filename of the output file will be
        ``{service-name}.sql``. If that exists, then we will use
        ``{service-name}-1.sql``, and if that exists ``{service-name}-2.sql``
        and so on.

        Args:
            obj: The ``PostgresDatabase`` object to use

        Keyword Args:
            filename: The name of the file to dump the database to.  If not,
                choose a filename for the dump.
            ssh_target: the ssh instance to use for running our postgres
                commands.  If not supplied, we will use the ``cluster``'s
                default ssh instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The dump failed because of some
                unexpected error.

        Returns:
            The stderr output of dumping the database, and the filename it was
            dumped to.

        """
        if filename is None:
            filename = f"{obj.service.name}.sql"
            i = 1
            while Path(filename).exists():
                filename = f"{obj.service.name}-{i}.sql"
                i += 1
        command = obj.render_for_dump()
        tmp_fd, file_path = tempfile.mkstemp()
        with os.fdopen(tmp_fd, "w") as fd:
            success, output = obj.cluster.ssh_noninteractive(
                command, output=fd, ssh_target=ssh_target, verbose=verbose
            )
            if success:
                fd.close()
                Path(file_path).rename(filename)
                return output, filename
            fd.close()
            Path(file_path).rename(filename + ".errors")
            _raise_if_binary_missing(obj, "pg_dump", output)
            msg = f'Failed to dump our Postgres db "{obj.db}" in {obj.host}:{obj.port}: {output}'  # noqa: E501
            raise obj.OperationFailed(msg)

    def load(
        self,
        obj: "PostgresDatabase",
        filepath: str,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Load the local SQL file ``filepath`` into the remote database.

        Args:
            obj: The ``PostgresDatabase`` object to use
            filepath: The name of the file to load

        Keyword Args:
            ssh_target: the ssh instance to use for running our postgres
                commands.  If not supplied, we will use the ``cluster``'s
                default ssh instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The load failed because of some
                unexpected error.

        Returns:
            The output of loading the file.

        """
        success, output, filename = obj.cluster.push_file(
            filepath, ssh_target=ssh_target, verbose=verbose
        )
        if not success:
            host = "NO HOST"
            if ssh_target:
                host = f"{ssh_target.name} ({ssh_target.ip_address})"
            msg = f"Failed to upload {filepath} to our cluster machine {host}: {output}"
            raise obj.OperationFailed(msg)
        command = obj.render_for_load().format(filename=filename)
        success, output = obj.cluster.ssh_noninteractive(
            command, ssh_target=ssh_target, verbose=verbose
        )
        if success:
            return output
        _raise_if_binary_missing(obj, "psql", output)
        msg = f'Failed to load "{filepath}" into database "{obj.db}" on {obj.host}:{obj.port}: {output}'  # noqa: E501
        raise obj.OperationFailed(msg)

    def server_version(
        self,
        obj: "PostgresDatabase",
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
        user: str | None = None,
        password: str | None = None,
    ) -> str:
        """
        Return the PostgreSQL version string of the remote Postgres server.

        Args:
            obj: The ``PostgresDatabase`` object to use

        Keyword Args:
            ssh_target: the ssh instance to use for running our postgres
                commands.  If not supplied, we will use the ``cluster``'s
                default ssh instance.
            verbose: If ``True`` run ssh in verbose mode.
            user: The user to use to bind to the database.
            password: The password to use to bind to the database.

        Raises:
            obj.OperationFailed: The command failed because of some
                unexpected error.

        Returns:
            The server version string.

        """
        command = obj.render_for_server_version(user=user, password=password)
        success, output = obj.cluster.ssh_noninteractive(
            command, ssh_target=ssh_target, verbose=verbose
        )
        if success:
            return output.strip()
        _raise_if_binary_missing(obj, "psql", output)
        msg = f"Failed to get Postgres version of remote server {obj.host}:{obj.port}: {output}"  # noqa: E501
        raise obj.OperationFailed(msg)

    def show_grants(
        self,
        obj: "PostgresDatabase",
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Show the role attributes for the database role on the remote database.

        Args:
            obj: The ``PostgresDatabase`` object to use

        Keyword Args:
            ssh_target: the ssh instance to use for running our postgres
                commands.  If not supplied, we will use the ``cluster``'s
                default ssh instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The command failed because of some
                unexpected error.

        Returns:
            The output of the ``\\du+`` command.

        """
        command = obj.render_for_show_grants()
        success, output = obj.cluster.ssh_noninteractive(
            command, ssh_target=ssh_target, verbose=verbose
        )
        if success:
            return output
        _raise_if_binary_missing(obj, "psql", output)
        msg = f'Failed to get role attributes for "{obj.user}" on remote server {obj.host}:{obj.port}: {output}'  # noqa: E501
        raise obj.OperationFailed(msg)


# ----------------------------------------
# Models
# ----------------------------------------


class PostgresDatabase(Model):
    """
    self.data here has the following structure:

        {
            'name': 'string',
            'service': 'string',
            'character_set': 'string',                   [optional, default='UTF8']
            'host': 'string',
            'db': 'string' ,
            'user': 'string',
            'pass': 'string',
            'port': 'string'                             [optional, default=5432]
        }
    """

    #: Objects.
    objects = PostgresDatabaseManager()
    #: Config section.
    config_section: str = "postgres"

    @property
    def pk(self) -> str:
        """
        Pk.

        Returns:
            Operation result.

        """
        return self.data["name"]

    @property
    def name(self) -> str:
        """
        Name.

        Returns:
            Operation result.

        """
        return self.data["name"]

    def secret(self, name: str) -> Secret:
        """
        Secret.

        Args:
            name: name.

        Returns:
            Operation result.

        """
        if "secrets" not in self.cache:
            self.cache["secrets"] = {}
        if name not in self.cache["secrets"]:
            if "." not in name:
                full_name = f"{self.service.secrets_prefix}{name}"
            else:
                full_name = name
            self.cache["secrets"][name] = Secret.objects.get(full_name)
        return self.cache["secrets"][name]

    def parse(self, key: str) -> str:
        """
        Deployfish supports putting 'config.KEY' as the value for the host and port keys
        in self.data

        Parse the value and dereference it from the live secrets for the service if
        necessary.

        Args:
            key: key.

        Returns:
            Operation result.

        """
        if isinstance(self.data[key], str):
            if self.data[key].startswith("config."):
                _, key = self.data[key].split(".")
                try:
                    value = self.secret(key).value
                except Secret.DoesNotExist:
                    msg = f'PostgresDatabase(pk="{self.name}"): Service(pk="{self.service.pk}") has no secret named "{key}"'  # noqa: E501
                    raise self.OperationFailed(msg) from None
                return value
        return self.data[key]

    @property
    def host(self) -> str:
        """
        Host.

        Returns:
            Operation result.

        """
        if "host" not in self.cache:
            self.cache["host"] = self.parse("host")
        return self.cache["host"]

    @property
    def user(self) -> str:
        """
        User.

        Returns:
            Operation result.

        """
        if "user" not in self.cache:
            self.cache["user"] = self.parse("user")
        return self.cache["user"]

    @property
    def db(self) -> str:
        """
        Db.

        Returns:
            Operation result.

        """
        if "db" not in self.cache:
            self.cache["db"] = self.parse("db")
        return self.cache["db"]

    @property
    def password(self) -> str:
        """
        Password.

        Returns:
            Operation result.

        """
        if "password" not in self.cache:
            self.cache["password"] = self.parse("pass")
        return self.cache["password"]

    @property
    def character_set(self) -> str:
        """
        Character set.

        Returns:
            Operation result.

        """
        if "character_set" not in self.cache:
            if "character_set" not in self.data:
                self.cache["character_set"] = "UTF8"
            else:
                self.cache["character_set"] = self.parse("character_set")
        return self.cache["character_set"]

    @property
    def port(self) -> int:
        """
        Port.

        Returns:
            Operation result.

        """
        if "port" not in self.cache:
            if "port" not in self.data:
                self.cache["port"] = 5432
            else:
                self.cache["port"] = self.parse("port")
        return self.cache["port"]

    @property
    def ssh_target(self) -> Instance | None:
        """
        Ssh target.

        Returns:
            Operation result.

        """
        if self.service.task_definition.is_fargate():
            return self.service.ssh_target
        return self.cluster.ssh_target

    @property
    def ssh_targets(self) -> Sequence[Instance]:
        """
        Ssh targets.

        Returns:
            Operation result.

        """
        return self.service.cluster.ssh_targets

    @property
    def service(self) -> Service:
        """
        Service.

        Returns:
            Operation result.

        """
        if "service" not in self.cache:
            config = get_config()
            data = config.get_section_item("services", self.data["service"])
            # We don't need the live service; we just need the service's cluster to exist  # noqa: E501
            self.cache["service"] = Service.new(data, "deployfish")
        return self.cache["service"]

    @service.setter
    def service(self, value: str) -> None:
        """
        Service.

        Args:
            value: value.

        """
        self.cache["service"] = value

    @property
    def cluster(self) -> Cluster:
        """
        Cluster.

        Returns:
            Operation result.

        """
        return self.service.cluster

    def create(
        self,
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Create.

        Args:
            root_user: root user.
            root_password: root password.
            ssh_target: ssh target.
            verbose: verbose.

        Returns:
            Operation result.

        """
        return self.objects.create(
            self, root_user, root_password, ssh_target=ssh_target, verbose=verbose
        )

    def update(
        self,
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Update.

        Args:
            root_user: root user.
            root_password: root password.
            ssh_target: ssh target.
            verbose: verbose.

        Returns:
            Operation result.

        """
        return self.objects.update(
            self, root_user, root_password, ssh_target=ssh_target, verbose=verbose
        )

    def validate(self, ssh_target: Instance = None, verbose: bool = False) -> str:  # noqa: FBT001, FBT002
        """
        Validate.

        Args:
            ssh_target: ssh target.
            verbose: verbose.

        Returns:
            Operation result.

        """
        return self.objects.validate(self, ssh_target=ssh_target, verbose=verbose)

    def dump(
        self,
        filename: str | None = None,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> tuple[str, str]:
        """
        Dump.

        Args:
            filename: filename.
            ssh_target: ssh target.
            verbose: verbose.

        Returns:
            Operation result.

        """
        return self.objects.dump(
            self, filename=filename, ssh_target=ssh_target, verbose=verbose
        )

    def load(
        self, filename: str, ssh_target: Instance = None, verbose: bool = False  # noqa: FBT001, FBT002
    ) -> str:
        """
        Load.

        Args:
            filename: filename.
            ssh_target: ssh target.
            verbose: verbose.

        Returns:
            Operation result.

        """
        return self.objects.load(self, filename, ssh_target=ssh_target, verbose=verbose)

    def server_version(
        self,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
        user: str | None = None,
        password: str | None = None,
    ) -> str:
        """
        Server version.

        Args:
            ssh_target: ssh target.
            verbose: verbose.
            user: user.
            password: password.

        Returns:
            Operation result.

        """
        return self.objects.server_version(
            self, ssh_target=ssh_target, verbose=verbose, user=user, password=password
        )

    def show_grants(
        self,
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Show grants.

        Args:
            ssh_target: ssh target.
            verbose: verbose.

        Returns:
            Operation result.

        """
        return self.objects.show_grants(self, ssh_target=ssh_target, verbose=verbose)

    def render_postgres_command(
        self,
        sql: str,
        dbname: str = "postgres",
        user: str | None = None,
        password: str | None = None,
        unaligned: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """
        Render postgres command.

        Args:
            sql: sql.
            dbname: dbname.
            user: user.
            password: password.
            unaligned: If ``True``, add ``--tuples-only --no-align`` for clean,
                single-line, machine-parseable output.

        Returns:
            Operation result.

        """
        user = user or self.user
        password = password or self.password
        flags = "--tuples-only --no-align " if unaligned else ""
        return (
            f"PGPASSWORD='{password}' psql --host={self.host} --username={user} "
            f'--port={self.port} --dbname={dbname} {flags}--command="{sql}"'
        )

    def render_for_create(self, root_user: str, root_password: str) -> str:
        """
        Render for create.

        Two separate ``psql -c`` invocations chained with ``&&``: PostgreSQL
        wraps a multi-statement query-protocol message in an implicit
        transaction, and ``CREATE DATABASE`` cannot run inside a transaction
        block, so it cannot be combined with ``CREATE ROLE`` in one ``-c``
        string.

        Args:
            root_user: root user.
            root_password: root password.

        Returns:
            Operation result.

        """
        role_sql = f"CREATE ROLE {self.user} LOGIN PASSWORD '{self.password}';"
        db_sql = (
            f"CREATE DATABASE {self.db} OWNER {self.user} "
            f"ENCODING '{self.character_set}';"
        )
        role_cmd = self.render_postgres_command(
            role_sql, user=root_user, password=root_password
        )
        db_cmd = self.render_postgres_command(
            db_sql, user=root_user, password=root_password
        )
        return f"{role_cmd} && {db_cmd}"

    def render_for_update(self, root_user: str, root_password: str) -> str:
        """
        Render for update.

        Args:
            root_user: root user.
            root_password: root password.

        Returns:
            Operation result.

        """
        sql = (
            f"ALTER ROLE {self.user} WITH PASSWORD '{self.password}';"
            f"GRANT ALL PRIVILEGES ON DATABASE {self.db} TO {self.user};"
            f"GRANT ALL ON SCHEMA public TO {self.user};"
        )
        return self.render_postgres_command(sql, user=root_user, password=root_password)

    def render_for_dump(self) -> str:
        """
        Render for dump.

        Returns:
            Operation result.

        """
        return (
            f"PGPASSWORD='{self.password}' pg_dump --format=plain --no-owner "
            f"--host={self.host} --username={self.user} --port={self.port} "
            f"--dbname={self.db}"
        )

    def render_for_load(self) -> str:
        """
        Render for load.

        Returns:
            Operation result.

        """
        return (
            f"PGPASSWORD='{self.password}' psql --host={self.host} "
            f"--username={self.user} --port={self.port} --dbname={self.db} "
            f"--file={{filename}} && rm {{filename}}"
        )

    def render_for_validate(self) -> str:
        """
        Render for validate.

        Returns:
            Operation result.

        """
        return self.render_postgres_command(
            "select version(), current_date;", unaligned=True
        )

    def render_for_server_version(
        self, user: str | None = None, password: str | None = None
    ) -> str:
        """
        Render for server version.

        Args:
            user: user.
            password: password.

        Returns:
            Operation result.

        """
        return self.render_postgres_command(
            "select version();", user=user, password=password, unaligned=True
        )

    def render_for_show_grants(self) -> str:
        """
        Render for show grants.

        Returns:
            Operation result.

        """
        return self.render_postgres_command(rf"\du+ {self.user}")
```

- [ ] **Step 3: Write the failing tests**

```python
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import deployfish.core.adapters  # noqa: F401  # pylint:disable=unused-import
from deployfish.plugins.postgres.models.postgres import (
    PostgresDatabase,
    _raise_if_binary_missing,
)


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
        assert _db().port == 5432

    def test_character_set_defaults_to_utf8(self) -> None:
        assert _db().character_set == "UTF8"

    def test_explicit_port_and_character_set(self) -> None:
        db = _db(port=5433, character_set="LATIN1")
        assert db.port == 5433
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
            "PGPASSWORD='rootpass' psql --host=myhost.example.com --username=root "
            "--port=5432 --dbname=postgres --command=\"ALTER ROLE myuser WITH "
            "PASSWORD 'mypass';GRANT ALL PRIVILEGES ON DATABASE mydb TO myuser;"
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
```

- [ ] **Step 4: Run tests to verify they fail with "module not found"**

Run: `.venv/bin/pytest tests/test_postgres_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deployfish.plugins.postgres'`

- [ ] **Step 5: Create the module files from Steps 1-2 above**

(Already specified in full above — write both files now.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_postgres_model.py -v`
Expected: PASS (all tests green)

- [ ] **Step 7: Commit**

```bash
git add deployfish/plugins/postgres/models/__init__.py deployfish/plugins/postgres/models/postgres.py tests/test_postgres_model.py
git commit -m "feat: add PostgresDatabase model and manager"
```

---

### Task 2: `PostgresDatabaseAdapter` and registry wiring

**Files:**
- Create: `deployfish/plugins/postgres/adapters/__init__.py`
- Create: `deployfish/plugins/postgres/adapters/deployfish/__init__.py`
- Create: `deployfish/plugins/postgres/adapters/deployfish/postgres.py`
- Test: `tests/test_postgres_model.py` (append to the file created in Task 1)

**Interfaces:**
- Consumes: `deployfish.core.adapters.abstract.Adapter`, `deployfish.registry.importer_registry`.
- Produces: `PostgresDatabaseAdapter(Adapter)` registered under the key `("PostgresDatabase", "deployfish")` in `deployfish.registry.importer_registry`, so `PostgresDatabase.new(data, "deployfish")` (used throughout Task 1 and the controller in Task 3) resolves correctly.

- [ ] **Step 1: Write `deployfish/plugins/postgres/adapters/deployfish/postgres.py`**

```python
from copy import deepcopy

from deployfish.core.adapters.abstract import Adapter


class PostgresDatabaseAdapter(Adapter):
    """
    Model postgres database adapter behavior.
    """

    def convert(self):
        """
        Convert.

        Returns:
            Operation result.

        """
        data = deepcopy(self.data)
        kwargs = {}
        return data, kwargs
```

- [ ] **Step 2: Write `deployfish/plugins/postgres/adapters/deployfish/__init__.py`**

```python
from deployfish.registry import importer_registry as registry

from .postgres import PostgresDatabaseAdapter

# -----------------------
# Adapter registrations
# -----------------------

# postgres
registry.register("PostgresDatabase", "deployfish", PostgresDatabaseAdapter)
```

- [ ] **Step 3: Write `deployfish/plugins/postgres/adapters/__init__.py`**

```python
from .deployfish import *  # noqa: F403
```

- [ ] **Step 4: Append this test to `tests/test_postgres_model.py`**

```python
class TestPostgresDatabaseAdapterRegistration:
    def test_adapter_is_registered(self) -> None:
        import deployfish.plugins.postgres.adapters  # noqa: F401
        from deployfish.registry import importer_registry

        adapter_cls = importer_registry.get("PostgresDatabase", "deployfish")
        assert adapter_cls.__name__ == "PostgresDatabaseAdapter"
```

- [ ] **Step 5: Run the full test file to verify everything still passes, including the new test**

Run: `.venv/bin/pytest tests/test_postgres_model.py -v`
Expected: PASS (all tests green, including `test_adapter_is_registered`)

- [ ] **Step 6: Commit**

```bash
git add deployfish/plugins/postgres/adapters tests/test_postgres_model.py
git commit -m "feat: add PostgresDatabaseAdapter and registry wiring"
```

---

### Task 3: `PostgresController` (cement CLI commands)

**Files:**
- Create: `deployfish/plugins/postgres/controllers/__init__.py`
- Create: `deployfish/plugins/postgres/controllers/postgres.py`

**Interfaces:**
- Consumes: `deployfish.controllers.crud.ReadOnlyCrudBase`, `deployfish.controllers.network.get_ssh_target`, `deployfish.controllers.utils.handle_model_exceptions`, `deployfish.core.models.{Model, RDSInstance}`, `deployfish.ext.ext_df_jinja2.{color, section_title}`, `deployfish.plugins.postgres.models.postgres.PostgresDatabase` (Task 1), `cement.{ex, shell}`, `jinja2.{ChoiceLoader, Environment, PackageLoader}`, `click`.
- Produces (used by Task 4's `__init__.py`): `class PostgresController(ReadOnlyCrudBase)` with `Meta.label = "postgres"`, registered by `app.handler.register(PostgresController)`.

- [ ] **Step 1: Write `deployfish/plugins/postgres/controllers/__init__.py`**

Empty file.

```python
```

- [ ] **Step 2: Write `deployfish/plugins/postgres/controllers/postgres.py`**

```python
from typing import Any

import click
from cement import ex, shell
from deployfish.controllers.crud import ReadOnlyCrudBase
from deployfish.controllers.network import get_ssh_target
from deployfish.controllers.utils import handle_model_exceptions
from deployfish.core.models import Model, RDSInstance
from deployfish.ext.ext_df_jinja2 import color, section_title
from deployfish.plugins.postgres.models.postgres import PostgresDatabase
from jinja2 import ChoiceLoader, Environment, PackageLoader


class PostgresController(ReadOnlyCrudBase):
    """
    Model postgres controller behavior.

    Args:
        *args: args.

    """

    class Meta:
        label = "postgres"
        description = "Work with PostgreSQL Databases"
        help = "Work with PostgreSQL Databases"
        stacked_type = "nested"

    #: Model.
    model: type[Model] = PostgresDatabase

    #: Help overrides.
    help_overrides: dict[str, str] = {
        "exists": "Show whether a PostgreSQL database connection exists in deployfish.yml",  # noqa: E501
        "list": "List available PostgreSQL database connections from deployfish.yml",
    }

    #: Info template.
    info_template: str = "detail--postgresdatabase.jinja2"

    #: List ordering.
    list_ordering: str = "Name"
    #: List result columns.
    list_result_columns: dict[str, Any] = {
        "Name": "name",
        "Host": "host",
        "DB": "db",
        "User": "user",
        "Password": "password",
    }

    def __init__(self, *args, **kwargs):
        """
        Initialize PostgresController.

        Args:
            *args: args.

        Keyword Args:
            kwargs: kwargs.

        """
        super().__init__(*args, **kwargs)
        # Set up Jinja2 environment with a ChoiceLoader to load templates from
        # the main application and the plugin
        #: Jinja2 env.
        self.jinja2_env = Environment(  # noqa: S701
            loader=ChoiceLoader(
                [
                    PackageLoader("deployfish", "templates"),
                    PackageLoader("deployfish.plugins.postgres", "templates"),
                ]
            )
        )
        # Import the color and section_title filters from
        # deployfish.ext.ext_df_jinja2 in order to render the templates
        self.jinja2_env.filters["color"] = color
        self.jinja2_env.filters["section_title"] = section_title

    @ex(
        help="Show details about a PostgreSQL database connection.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            )
        ],
    )
    @handle_model_exceptions
    def info(self) -> None:
        """
        Show details about a PostgreSQL database in AWS.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_aws(self.app.pargs.pk)
        # Use the Jinja2 environment to render the template rather than the
        # default Cement renderer that only takes a local template name
        template = self.jinja2_env.get_template(self.info_template)
        self.app.print(template.render(obj=obj))

    @ex(
        help="Create a PostgreSQL role and database in the remote PostgreSQL server.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            ),
            (
                ["--root-password"],
                {
                    "help": "the password of the root user for the PostgreSQL server",
                    "default": None,
                    "dest": "root_password",
                },
            ),
            (
                ["-c", "--choose"],
                {
                    "help": (
                        "Choose from all available ssh targets instead of choosing one "
                        "automatically.",
                    ),
                    "default": False,
                    "dest": "choose",
                    "action": "store_true",
                },
            ),
            (
                ["-v", "--verbose"],
                {
                    "help": "Show all SSH output.",
                    "default": False,
                    "dest": "verbose",
                    "action": "store_true",
                },
            ),
        ],
        description="""
Create a role and database in a remote PostgreSQL server.
""",
    )
    @handle_model_exceptions
    def create(self):
        """
        Create.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        # The DbInstanceIdentifier should be the short hostname from the host key
        db_instance_name = obj.host.split(".")[0]
        rds_instance = RDSInstance.objects.get(db_instance_name)
        if not self.app.pargs.root_password:
            if rds_instance.secret_enabled:
                self.app.pargs.root_password = rds_instance.root_password
            else:
                p = shell.Prompt("DB root password")
                self.app.pargs.root_password = p.prompt()
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        output = obj.create(
            rds_instance.root_user,
            self.app.pargs.root_password,
            ssh_target=target,
            verbose=self.app.pargs.verbose,
        )
        lines = [
            click.style(
                f'Created database "{obj.db}" in postgres server {obj.host}:{obj.port}.',
                fg="green",
            ),
            click.style(
                f'Created role "{obj.user}" in postgres server {obj.host}:{obj.port} '
                f'and made it owner of database "{obj.db}".',
                fg="green",
            ),
        ]
        if output:
            lines.append(click.style("\nPostgreSQL output:\n", fg="yellow"))
            lines.append(output)
        self.app.print("\n".join(lines))

    @ex(
        help="Update a PostgreSQL role's password and grants in the remote "
        "PostgreSQL server.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            ),
            (
                ["--root-password"],
                {
                    "help": "the password of the root user for the PostgreSQL server",
                    "default": None,
                    "dest": "root_password",
                },
            ),
            (
                ["-c", "--choose"],
                {
                    "help": (
                        "Choose from all available ssh targets instead of choosing one "
                        "automatically.",
                    ),
                    "default": False,
                    "dest": "choose",
                    "action": "store_true",
                },
            ),
            (
                ["-v", "--verbose"],
                {
                    "help": "Show all SSH output.",
                    "default": False,
                    "dest": "verbose",
                    "action": "store_true",
                },
            ),
        ],
        description="""
Update an existing role's password and grants in a remote PostgreSQL server.
""",
    )
    @handle_model_exceptions
    def update(self):
        """
        Update.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        db_instance_name = obj.host.split(".")[0]
        rds_instance = RDSInstance.objects.get(db_instance_name)
        if not self.app.pargs.root_password:
            if rds_instance.secret_enabled:
                self.app.pargs.root_password = rds_instance.root_password
            else:
                p = shell.Prompt("DB root password")
                self.app.pargs.root_password = p.prompt()
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        output = obj.update(
            rds_instance.root_user,
            self.app.pargs.root_password,
            ssh_target=target,
            verbose=self.app.pargs.verbose,
        )
        lines = [
            click.style(
                f'Updated role "{obj.user}" in postgres server {obj.host}:{obj.port} '
                f'and re-granted privileges on database "{obj.db}".',
                fg="green",
            ),
        ]
        if output:
            lines.append(click.style("\nPostgreSQL output:\n", fg="yellow"))
            lines.append(output)
        self.app.print("\n".join(lines))

    @ex(
        help="Validate that a PostgreSQL database and role exist in the remote "
        "PostgreSQL server and has the password we expect.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            ),
            (
                ["-c", "--choose"],
                {
                    "help": (
                        "Choose from all available ssh targets instead of choosing one "
                        "automatically.",
                    ),
                    "default": False,
                    "dest": "choose",
                    "action": "store_true",
                },
            ),
            (
                ["-v", "--verbose"],
                {
                    "help": "Show all SSH output.",
                    "default": False,
                    "dest": "verbose",
                    "action": "store_true",
                },
            ),
        ],
        description="""
Validate that a role in a remote PostgreSQL server exists and has the password
we expect.
""",
    )
    @handle_model_exceptions
    def validate(self):
        """
        Validate.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        obj.validate(ssh_target=target, verbose=self.app.pargs.verbose)
        lines = [
            click.style(
                f'PostgreSQL role "{obj.user}" in postgres server {obj.host}:{obj.port} '
                f"exists and has the password we expect.",
                fg="green",
            )
        ]
        self.app.print("\n".join(lines))

    @ex(
        help="Dump the contents of a remote PostgreSQL database to local file.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            ),
            (
                ["--dumpfile"],
                {
                    "help": "Write the SQL dump to this file.",
                    "default": None,
                    "dest": "dumpfile",
                },
            ),
            (
                ["-c", "--choose"],
                {
                    "help": (
                        "Choose from all available ssh targets instead of choosing one "
                        "automatically.",
                    ),
                    "default": False,
                    "dest": "choose",
                    "action": "store_true",
                },
            ),
            (
                ["-v", "--verbose"],
                {
                    "help": "Show all SSH output.",
                    "default": False,
                    "dest": "verbose",
                    "action": "store_true",
                },
            ),
        ],
        description="""
Dump the contents of a PostgreSQL database to a local file.  If "--dumpfile" is
not supplied, the filename of the output file will be "{service-name}.sql". If
that exists, then we will use "{service-name}-1.sql", and if that exists
"{service-name}-2.sql" and so on.
""",
    )
    @handle_model_exceptions
    def dump(self):
        """
        Dump.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        _, output_filename = obj.dump(
            filename=self.app.pargs.dumpfile,
            ssh_target=target,
            verbose=self.app.pargs.verbose,
        )
        lines = [
            click.style(
                f'Dumped database "{obj.db}" in postgres server {obj.host}:{obj.port} '
                f'to "{output_filename}".',
                fg="green",
            )
        ]
        self.app.print("\n".join(lines))

    @ex(
        help="Load the contents of a local SQL file into an existing PostgreSQL "
        "database.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            ),
            (["sqlfile"], {"help": "the filename of the SQL file to load"}),
            (
                ["-c", "--choose"],
                {
                    "help": (
                        "Choose from all available ssh targets instead of choosing one "
                        "automatically.",
                    ),
                    "default": False,
                    "dest": "choose",
                    "action": "store_true",
                },
            ),
            (
                ["-v", "--verbose"],
                {
                    "help": "Show all SSH output.",
                    "default": False,
                    "dest": "verbose",
                    "action": "store_true",
                },
            ),
        ],
        description="""
Load the contents of a local SQL file into an existing PostgreSQL database in
the remote PostgreSQL server.
""",
    )
    @handle_model_exceptions
    def load(self):
        """
        Load.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        output = obj.load(
            self.app.pargs.sqlfile, ssh_target=target, verbose=self.app.pargs.verbose
        )
        lines = [
            click.style(
                f'Loaded file "{self.app.pargs.sqlfile}" into database "{obj.db}" on '
                f"postgres server {obj.host}:{obj.port}",
                fg="green",
            )
        ]
        if output.strip():
            lines.append(
                click.style(f"Output from `psql` command:\n{output}", fg="red")
            )
        self.app.print("\n".join(lines))

    @ex(
        help="Show the role attributes for our role in the remote PostgreSQL server.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            ),
            (
                ["-c", "--choose"],
                {
                    "help": (
                        "Choose from all available ssh targets instead of choosing one "
                        "automatically.",
                    ),
                    "default": False,
                    "dest": "choose",
                    "action": "store_true",
                },
            ),
            (
                ["-v", "--verbose"],
                {
                    "help": "Show all SSH output.",
                    "default": False,
                    "dest": "verbose",
                    "action": "store_true",
                },
            ),
        ],
        description="""
Show the role attributes for our role in the remote PostgreSQL server.
""",
    )
    @handle_model_exceptions
    def show_grants(self):
        """
        Show grants.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        output = obj.show_grants(ssh_target=target, verbose=self.app.pargs.verbose)
        self.app.print(output)

    @ex(
        help="Show the PostgreSQL version for the remote PostgreSQL server.",
        arguments=[
            (
                ["pk"],
                {"help": "the name of the PostgreSQL connection in deployfish.yml"},
            ),
            (
                ["-c", "--choose"],
                {
                    "help": (
                        "Choose from all available ssh targets instead of choosing one "
                        "automatically.",
                    ),
                    "default": False,
                    "dest": "choose",
                    "action": "store_true",
                },
            ),
            (
                ["-v", "--verbose"],
                {
                    "help": "Show all SSH output.",
                    "default": False,
                    "dest": "verbose",
                    "action": "store_true",
                },
            ),
        ],
        description="""
Print the PostgreSQL version of the remote PostgreSQL server.
""",
    )
    @handle_model_exceptions
    def server_version(self):
        """
        Server version.
        """
        loader = self.loader(self)
        obj = loader.get_object_from_deployfish(self.app.pargs.pk)
        target = get_ssh_target(self.app, obj, choose=self.app.pargs.choose)
        self.app.print(
            obj.server_version(ssh_target=target, verbose=self.app.pargs.verbose)
        )
```

- [ ] **Step 3: Verify the controller imports cleanly**

Run: `.venv/bin/python -c "from deployfish.plugins.postgres.controllers.postgres import PostgresController; print(PostgresController.Meta.label)"`
Expected: prints `postgres`

- [ ] **Step 4: Commit**

```bash
git add deployfish/plugins/postgres/controllers
git commit -m "feat: add PostgresController with 8 CLI verbs"
```

---

### Task 4: Plugin bootstrap, template, docs, and smoke test

**Files:**
- Create: `deployfish/plugins/postgres/hooks.py`
- Create: `deployfish/plugins/postgres/__init__.py`
- Create: `deployfish/plugins/postgres/templates/__init__.py`
- Create: `deployfish/plugins/postgres/templates/detail--postgresdatabase.jinja2`
- Create: `docs/source/plugins/postgres.rst`
- Test: `tests/test_postgres_plugin_loading.py`

**Interfaces:**
- Consumes: `PostgresController` (Task 3), `deployfish.plugins.postgres.adapters` (Task 2), `cement.App`, `deployfish.config.Config` (for `add_processable_section`), `deployfish.main.DeployfishApp`.
- Produces: `deployfish.plugins.postgres.load(app)` — the entry point cement's built-in plugin handler calls automatically (no registration code needed elsewhere).

- [ ] **Step 1: Write `deployfish/plugins/postgres/hooks.py`**

```python
from typing import TYPE_CHECKING

from cement import App

if TYPE_CHECKING:
    from deployfish.config import Config


def pre_config_interpolate_add_postgres_section(app: App, obj: "type[Config]") -> None:  # noqa: ARG001
    """
    Add our "postgres" section to the list of sections on which keyword interpolation
    will be run

    Args:
        app: out cement app
        obj: the :py:class:`deployfish.config.Config` class

    """
    obj.add_processable_section("postgres")
```

- [ ] **Step 2: Write `deployfish/plugins/postgres/__init__.py`**

```python
from pathlib import Path

from cement import App

from . import adapters  # noqa:F401
from .controllers.postgres import PostgresController
from .hooks import pre_config_interpolate_add_postgres_section

__version__ = "1.0.0"


def add_template_dir(app: App):
    """
    Add template dir.

    Args:
        app: app.

    """
    path = str(Path(__file__).parent / "templates")
    app.add_template_dir(path)


def load(app: App) -> None:
    """
    Load.

    Args:
        app: app.

    """
    app.handler.register(PostgresController)
    app.hook.register("post_setup", add_template_dir)
    app.hook.register(
        "pre_config_interpolate", pre_config_interpolate_add_postgres_section
    )
```

- [ ] **Step 3: Write `deployfish/plugins/postgres/templates/__init__.py`**

Empty file.

```python
```

- [ ] **Step 4: Write `deployfish/plugins/postgres/templates/detail--postgresdatabase.jinja2`**

```jinja2
{% from 'macros/utils.jinja2' import heading, subsection, subobject, tags -%}
{{ subobject('PostgreSQL Database', obj.name) }}
  pk                  :     {{ obj.pk }}
  name                :     {{ obj.name }}
  host                :     {{ obj.host }}
  port                :     {{ obj.port }}
  database            :     {{ obj.db }}
  user                :     {{ obj.user }}
  password            :     {{ obj.password }}
```

- [ ] **Step 5: Write `docs/source/plugins/postgres.rst`**

```rst
Postgres Plugin
================

``deployfish-postgres`` is a plugin that allows you to manage databases in remote PostgreSQL servers in AWS.

* ``deploy postgres create {name}``: Create a role and database, with the role as owner.
* ``deploy postgres update {name}``: Update the role's password and re-grant privileges
* ``deploy postgres validate {name}``: Validate that the username/password combination is valid
* ``deploy postgres dump {name}``: Dump PostgreSQL databases as SQL files to local file systems.
* ``deploy postgres load {name} {filename}``: Load a local SQL file into remote PostgreSQL databases
* ``deploy postgres show-grants {name}``: Show role attributes for your role

``{name}`` above refers to the ``name`` of a PostgreSQL connection from the ``postgres:`` section of
your ``deployfish.yml`` file.  See below for how the ``postgres:`` connection works.

Configure deployfish-postgres
------------------------------

First follow the instructions for installing and configuring deployfish, then
add this stanza to your ``~/.deployfish.yml`` file:

    plugin.postgres:
        enabled: true

NOTE: ``~/.deployfish.yml`` is the config file for deployfish itself.  This is different from
the ``deployfish.yml`` file that defines your services and tasks.

Instrument your deployfish.yml
--------------------------------

``deployfish-postgres`` looks in your ``deployfish.yml`` file (the one with your services and
task definitions, not the ``~/.deployfish.yml`` config file for deployfish itself) for a
section named ``postgres``, which has definitions of postgres databases::

    postgres:
    - name: test
        service: service-test
        host: my-remote-rds-host.amazonaws.com
        db: mydb
        user: myuser
        pass: password

    - name: config-test
        service: service-test
        host: config.DB_HOST
        db: config.DB_NAME
        user: config.DB_USER
        pass: config.DB_PASSWORD

    services:
    - name: dftest-test
        cluster: my-cluster
        environment: test
        config:
        - DEBUG=False
        - DB_HOST=${terraform.rds_address}
        - DB_NAME=dftest
        - DB_USER=dftest_u
        - DB_PASSWORD:secure:kms_key_arn=${env.DB_PASSWORD}

Entries in the ``postgres:`` section must minimally define these keys:

* ``name``: the name of the connection.  This will be used in all the ``deploy postgres`` commands as the connection name.
* ``service``: the name of a service in the ``services:`` section.  This will be used to determine which host we use to use for SSH when doing our postgres commands
* ``host``: the hostname of the remote PostgreSQL server
* ``db``: the name of the database to work with in ``host``
* ``user``: the username of the role to use to authenticate to ``host``
* ``pass``: the password of the role to use to authenticate to ``host``

These are optional keys that you can add to your connection definition:

* ``port``: the port to connect to on the remote PostgreSQL server.  Default: 5432
* ``character_set``: set the ``ENCODING`` of your database to this (used only for ``deploy postgres create``, since PostgreSQL's ``ENCODING`` cannot be changed after a database is created).  Default: ``UTF8``.

As you can see in the examples above, you can either hard code ``host``, ``db``, ``user`` and ``password`` in or you can reference ``config`` parameters from the ``config:`` section of the definition of our service.  For the latter, ``deployfish-postgres`` will retrieve those parameters directly from AWS SSM Parameter Store, so ensure you write the service config to AWS before trying to establish a PostgreSQL connection.
```

- [ ] **Step 6: Write the smoke test `tests/test_postgres_plugin_loading.py`**

```python
from deployfish.main import DeployfishApp


class TestPostgresPluginLoading:
    def test_postgres_plugin_is_loaded(self) -> None:
        app = DeployfishApp()
        app.setup()
        assert "postgres" in app.plugin.get_loaded_plugins()

    def test_postgres_controller_has_all_eight_verbs(self) -> None:
        app = DeployfishApp()
        app.setup()
        controller_cls = app.handler.get("controller", "postgres", setup=False)
        exposed = {
            member
            for member in dir(controller_cls)
            if hasattr(getattr(controller_cls, member), "__cement_meta__")
        }
        expected = {
            "info",
            "create",
            "update",
            "validate",
            "dump",
            "load",
            "show_grants",
            "server_version",
        }
        assert expected <= exposed
```

- [ ] **Step 7: Run the smoke test**

Run: `.venv/bin/pytest tests/test_postgres_plugin_loading.py -v`
Expected: PASS. If `test_postgres_plugin_is_loaded` fails, check for an import error in `deployfish/plugins/postgres/__init__.py` first — cement's plugin auto-loader silently drops a plugin whose module fails to import in some configurations, so a failure here often means Task 1-3's files have a typo, not that the wiring itself is wrong.

- [ ] **Step 8: Manually confirm the CLI surface**

Run: `.venv/bin/python -m deployfish.main --help 2>&1 | grep -A2 postgres` (or `deploy --help` if the console script is on `$PATH` inside the venv)
Expected: a `postgres` subcommand section appears alongside `mysql`.

Run: `.venv/bin/python -c "
from deployfish.main import DeployfishApp
app = DeployfishApp(argv=['postgres', '--help'])
app.setup()
app.run()
"`
Expected: help text listing `info`, `create`, `update`, `validate`, `dump`, `load`, `show-grants`, `server-version`.

- [ ] **Step 9: Commit**

```bash
git add deployfish/plugins/postgres/hooks.py deployfish/plugins/postgres/__init__.py deployfish/plugins/postgres/templates docs/source/plugins/postgres.rst tests/test_postgres_plugin_loading.py
git commit -m "feat: wire up postgres plugin bootstrap, template, and docs"
```

---

### Task 5: Quality gate

**Files:**
- Modify: none (verification only)

**Interfaces:**
- Consumes: every file created in Tasks 1-4.
- Produces: nothing new — this task only verifies and fixes.

- [ ] **Step 1: Run ruff on all touched files**

Run: `.venv/bin/ruff check deployfish/plugins/postgres/ tests/test_postgres_model.py tests/test_postgres_plugin_loading.py`
Expected: no errors. Fix any reported issue in the offending file and re-run until clean.

- [ ] **Step 2: Run mypy on all touched files**

Run: `.venv/bin/mypy deployfish/plugins/postgres/`
Expected: no errors. Fix any reported issue and re-run until clean.

- [ ] **Step 3: Run the napoleon docstring gate**

Run: `make napoleon-gate`
Expected: no new violations versus baseline. Fix any reported issue (missing `Args:`/`Returns:` sections, missing `#:` attribute comments, etc. — see this project's `CLAUDE.md` "Documentation Contract" section) and re-run until clean.

- [ ] **Step 4: Run the full test suite once more to confirm no regressions**

Run: `.venv/bin/pytest tests/test_postgres_model.py tests/test_postgres_plugin_loading.py -v`
Expected: PASS

- [ ] **Step 5: Commit any quality-gate fixes**

```bash
git add deployfish/plugins/postgres tests/test_postgres_model.py tests/test_postgres_plugin_loading.py
git commit -m "fix: address ruff/mypy/napoleon-gate findings in postgres plugin"
```

(Skip this commit if Steps 1-3 reported nothing to fix.)

---

## Self-Review

**Spec coverage** (against `docs/adr/0003-postgres-plugin.md`):
- Command set (info/create/update/validate/dump/load/show-grants/server-version) → Task 3.
- Config shape, `character_set` default, no `collation` → Task 1 (`PostgresDatabase` properties).
- Two-invocation `create` (transaction-block fix) → Task 1 (`render_for_create`) + Task 1 test `test_render_for_create_is_two_chained_invocations`.
- `update` with re-grant, no encoding change → Task 1 (`render_for_update`).
- `validate`/`server-version` via `-t -A`, `validate` doesn't parse output → Task 1.
- `show-grants` via `\du+` → Task 1 (`render_for_show_grants`).
- Plain-SQL `dump`/`load`, filename-collision retry → Task 1 (`PostgresDatabaseManager.dump`).
- `PGPASSWORD` auth, bare `psql`/`pg_dump` → Task 1 (`render_postgres_command`, `render_for_dump`).
- Missing-binary detection → Task 1 (`_raise_if_binary_missing`, wired into every manager method) + tests.
- `RDSInstance` reuse → Task 3 (`create`/`update` controller methods).
- Naming conventions → Tasks 1-4 throughout.
- No new plugin-loading wiring → Task 4 Step 7-8 verifies this is true rather than assuming it.
- No shared base class → Task 1 defines `PostgresDatabase`/`PostgresDatabaseManager` standalone, no inheritance from mysql's classes.

**Placeholder scan:** none found — every step has literal file contents or an exact command to run.

**Type consistency:** `PostgresDatabase`/`PostgresDatabaseManager`/`PostgresDatabaseAdapter`/`_raise_if_binary_missing`/`render_postgres_command` names and signatures are identical across Tasks 1-4 wherever referenced.

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-26-postgres-plugin.md`.** Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
