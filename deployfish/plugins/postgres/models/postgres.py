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
    for line_raw in output.splitlines():
        line = line_raw.strip()
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
        self,
        obj: "PostgresDatabase",
        ssh_target: Instance = None,
        verbose: bool = False,  # noqa: FBT001, FBT002
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
        r"""
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
