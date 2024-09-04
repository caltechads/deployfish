import os
import tempfile
from typing import Optional, Sequence, Tuple, List, cast

from deployfish.config import get_config
from deployfish.core.models import Manager, Model, Secret, Service, Instance, Cluster


# ----------------------------------------
# Managers
# ----------------------------------------

class MySQLDatabaseManager(Manager):

    def get(self, pk: str, **_) -> Model:
        """
        Get the MySQLDatabase object from the config file.

        Args:
            pk: the name of the database to get from the config file.

        Raises:
            MySQLDatabase.DoesNotExist: No MySQLDatabase object with that name
                exists in the config file.

        Returns:
            The MySQLDatabase object.
        """
        # hint: (str["{name}"])
        config = get_config()
        section = config.get_section('mysql')
        databases = {}
        for data in section:
            databases[data['name']] = data
        if pk in databases:
            return MySQLDatabase.new(databases[pk], 'deployfish')
        raise MySQLDatabase.DoesNotExist(
            'Could not find an MySQLDatabase config named "{}" in deployfish.yml:mysql'.format(pk)
        )

    def list(self, service_name: str = None, **_) -> Sequence["MySQLDatabase"]:
        """
        List the MySQLDatabase objects in the config file.

        Returns:
            A list of MySQLDatabase objects.
        """
        # hint: (str["{service_name}"], int)
        config = get_config()
        section = config.get_section('mysql')
        databases = [MySQLDatabase.new(db, 'deployfish') for db in section]
        if service_name:
            databases = [db for db in databases if db.data['service'] == service_name]
        return cast(List["MySQLDatabase"], databases)

    def save(  # type: ignore  # pylint:disable=arguments-differ
        self,
        obj: "MySQLDatabase",
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        """
        This is an alias for :py:meth:`create`.

        Args:
            obj: The ``MySQLDatabase`` object
            root_user: The root user to use to connect to the database.
            root_password: The root password to use to connect to the database.

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The create failed because of some
                unexpected error.

        Returns:
            The output of the validation commands.
        """
        return self.create(obj, root_user, root_password, ssh_target=ssh_target, verbose=verbose)

    def create(
        self,
        obj: "MySQLDatabase",
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        """
        Create the database and user for ``obj``, and assign appropriate grants to
        the user.

        Args:
            obj: The ``MySQLDatabase`` object
            root_user: The root user to use to connect to the database.
            root_password: The root password to use to connect to the database.

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The create failed because of some
                unexpected error.

        Returns:
            The output of the validation commands.
        """
        version = self.major_server_version(
            obj,
            user=root_user,
            password=root_password,
            verbose=verbose,
            ssh_target=ssh_target
        )
        command = obj.render_for_create(root_user, root_password, version=version)
        status, output = obj.cluster.ssh_noninteractive(
            command,
            ssh_target=ssh_target,
            verbose=verbose
        )
        if status:
            return output
        raise obj.OperationFailed(
            'Failed to create database "{}" and/or user "{}" on {}:{}: {}'.format(
                obj.db,
                obj.user,
                obj.host,
                obj.port,
                output
            )
        )

    def update(
        self,
        obj: "MySQLDatabase",
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        """
        Update the grants and password for the database user on ``obj``.

        Args:
            obj: The ``MySQLDatabase`` object
            root_user: The root user to use to connect to the database.
            root_password: The root password to use to connect to the database.

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The update failed because of some
                unexpected error.

        Returns:
            The output of the update commands.
        """
        version = self.major_server_version(
            obj,
            user=root_user,
            password=root_password,
            verbose=verbose,
            ssh_target=ssh_target
        )
        command = obj.render_for_update(root_user, root_password, version=version)
        success, output = obj.cluster.ssh_noninteractive(
            command,
            ssh_target=ssh_target,
            verbose=verbose
        )
        if success:
            return output
        raise obj.OperationFailed(
            'Failed to update database "{}" and/or user "{}" on {}:{}: {}'.format(
                obj.db,
                obj.user,
                obj.host,
                obj.port,
                output
            )
        )

    def validate(
        self,
        obj: "MySQLDatabase",
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        """
        Validate that the database and user exist on the target MySQL server.

        Args:
            obj: The ``MySQLDatabase`` object to validate.

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The validation failed because of some
                unexpected error.

        Returns:
            The output of the validation commands.
        """
        command = obj.render_for_validate()
        success, output = obj.cluster.ssh_noninteractive(
            command,
            ssh_target=ssh_target,
            verbose=verbose
        )
        if success:
            return output
        raise obj.OperationFailed(
            'Failed to validate user "{}" on {}:{}: {}'.format(
                obj.user,
                obj.host,
                obj.port,
                output
            )
        )

    def dump(
        self,
        obj: "MySQLDatabase",
        filename: str = None,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> Tuple[str, str]:
        """
        Use ``mysqldump`` to dump the remote database as SQL to a local file.

        If ``filename`` is not supplied, the filename of the output file will be
        ``{service-name}.sql``. If that exists, then we will use
        ``{service-name}-1.sql``, and if that exists ``{service-name}-2.sql``
        and so on.

        Args:
            obj: The ``MySQLDatabase`` object to us

        Keyword Args:
            filename: The name of the file to dump the database to.  If not,
                choose a filename for the dump.
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The dump failed because of some
                unexpected error.

        Returns:
            The stderr output of dumping the database.
        """
        if filename is None:
            filename = "{}.sql".format(obj.service.name)
            i = 1
            while os.path.exists(filename):
                filename = "{}-{}.sql".format(obj.service.name, i)
                i += 1
        command = obj.render_for_dump()
        tmp_fd, file_path = tempfile.mkstemp()
        with os.fdopen(tmp_fd, 'w') as fd:
            success, output = obj.cluster.ssh_noninteractive(
                command,
                output=fd,
                ssh_target=ssh_target,
                verbose=verbose
            )
            if success:
                fd.close()
                os.rename(file_path, filename)
                return output, filename
            fd.close()
            os.rename(file_path, filename + ".errors")
            raise obj.OperationFailed('Failed to dump our MySQL db "{}" in {}:{}: {}'.format(
                obj.db,
                obj.host,
                obj.port,
                output
            ))

    def load(
        self,
        obj: "MySQLDatabase",
        filepath: str,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        """
        Load the local SQL file ``filepath`` into the remote database.

        Args:
            obj: The ``MySQLDatabase`` object to us
            filepath: The name of the file to load

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The load failed because of some
                unexpected error.

        Returns:
            The output of loading the file.
        """
        success, output, filename = obj.cluster.push_file(filepath, ssh_target=ssh_target, verbose=verbose)
        if not success:
            host = 'NO HOST'
            if ssh_target:
                host = f'{ssh_target.name} ({ssh_target.ip_address})'
            raise obj.OperationFailed(
                'Failed to upload {} to our cluster machine {}: {}'.format(
                    filepath, host, output
                )
            )
        command = obj.render_for_load().format(filename=filename)
        success, output = obj.cluster.ssh_noninteractive(command, ssh_target=ssh_target, verbose=verbose)
        if success:
            return output
        raise obj.OperationFailed(
            'Failed to load "{}" into database "{}" on {}:{}: {}'.format(
                filepath,
                obj.db,
                obj.host,
                obj.port,
                output
            )
        )

    def major_server_version(
        self,
        obj: "MySQLDatabase",
        ssh_target: Instance = None,
        verbose: bool = False,
        user: str = None,
        password: str = None
    ):
        """
        Return the major.minor version of the MySQL server.

        Example:
            If the server version is ``5.7.22``, then we will return ``5.7``.

        Args:
            obj: The ``MySQLDatabase`` object to us

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.
            user: The user to use to bind to the database.
            password: The password to use to bind to the database.

        Raises:
            obj.OperationFailed: The command failed because of some
                unexpected error.

        Returns:
            The major.minor version of the MySQL server.
        """
        version = self.server_version(obj, ssh_target=ssh_target, verbose=verbose, user=user, password=password)
        version = version.rsplit('.', 1)[0]
        return version

    def server_version(
        self,
        obj: "MySQLDatabase",
        ssh_target: Instance = None,
        verbose: bool = False,
        user: str = None,
        password: str = None
    ) -> str:
        """
        Return the MySQL version of the MySQL server.

        Example:
            If the server version is ``5.7.22``, then we will return ``5.7.22``.

        Args:
            obj: The ``MySQLDatabase`` object to us

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.
            user: The user to use to bind to the database.
            password: The password to use to bind to the database.

        Raises:
            obj.OperationFailed: The command failed because of some
                unexpected error.

        Returns:
            The server version
        """
        command = obj.render_for_server_version(user=user, password=password)
        success, output = obj.cluster.ssh_noninteractive(command, ssh_target=ssh_target, verbose=verbose)
        if success:
            return output.split('\n')[3][2:-2].strip()
        raise obj.OperationFailed('Failed to get MySQL version of remote server {}:{}: {}'.format(
            obj.host,
            obj.port,
            output
        ))

    def show_grants(
        self,
        obj: "MySQLDatabase",
        ssh_target: Instance = None,
        verbose: bool = False,
    ) -> str:
        """
        Show the GRANTs for the database user on the remote database.

        Args:
            obj: The ``MySQLDatabase`` object to us

        Keyword Args:
            ssh_target: the ssh instance to use for running our mysql commands.
                If not supplied, we will use the ``cluster``'s default ssh
                instance.
            verbose: If ``True`` run ssh in verbose mode.

        Raises:
            obj.OperationFailed: The command failed because of some
                unexpected error.

        Returns:
            The output of the ``SHOW GRANTS` command.
        """
        command = obj.render_for_show_grants()
        success, output = obj.cluster.ssh_noninteractive(command, ssh_target=ssh_target, verbose=verbose)
        if success:
            return output
        raise obj.OperationFailed('Failed to get grants for user "{}" on remote server {}:{}: {}'.format(
            obj.user,
            obj.host,
            obj.port,
            output
        ))


# ----------------------------------------
# Models
# ----------------------------------------

class MySQLDatabase(Model):
    """
    self.data here has the following structure:

        {
            'name': 'string',
            'service': 'string',
            'character_set': 'string',                   [optional, default='utf8']
            'collation': 'string',                       [optional, default='utf8_unicode_ci']
            'host': 'string',
            'db': 'string' ,
            'user': 'string',
            'pass': 'string',
            'port': 'string'                             [optional, default=3306]
        }
    """

    objects = MySQLDatabaseManager()
    config_section: str = 'mysql'

    @property
    def pk(self) -> str:
        return self.data['name']

    @property
    def name(self) -> str:
        return self.data['name']

    def secret(self, name: str) -> Secret:
        if 'secrets' not in self.cache:
            self.cache['secrets'] = {}
        if name not in self.cache['secrets']:
            if "." not in name:
                full_name = '{}{}'.format(self.service.secrets_prefix, name)
            else:
                full_name = name
            self.cache['secrets'][name] = Secret.objects.get(full_name)
        return self.cache['secrets'][name]

    def parse(self, key: str) -> str:
        """
        deployfish supports putting 'config.KEY' as the value for the host and port keys in self.data

        Parse the value and dereference it from the live secrets for the service if necessary.
        """
        if isinstance(self.data[key], str):
            if self.data[key].startswith('config.'):
                _, key = self.data[key].split('.')
                try:
                    value = self.secret(key).value
                except Secret.DoesNotExist:
                    raise self.OperationFailed(
                        'MySQLDatabase(pk="{}"): Service(pk="{}") has no secret named "{}"'.format(
                            self.name,
                            self.service.pk,
                            key
                        )
                    )
                return value
        return self.data[key]

    @property
    def host(self) -> str:
        if 'host' not in self.cache:
            self.cache['host'] = self.parse('host')
        return self.cache['host']

    @property
    def user(self) -> str:
        if 'user' not in self.cache:
            self.cache['user'] = self.parse('user')
        return self.cache['user']

    @property
    def db(self) -> str:
        if 'db' not in self.cache:
            self.cache['db'] = self.parse('db')
        return self.cache['db']

    @property
    def password(self) -> str:
        if 'password' not in self.cache:
            self.cache['password'] = self.parse('pass')
        return self.cache['password']

    @property
    def character_set(self) -> str:
        if 'character_set' not in self.cache:
            if 'character_set' not in self.data:
                self.cache['character_set'] = 'utf8'
            else:
                self.cache['character_set'] = self.parse('character_set')
        return self.cache['character_set']

    @property
    def collation(self) -> str:
        if 'collation' not in self.cache:
            if 'collation' not in self.data:
                self.cache['collation'] = 'utf8_unicode_ci'
            else:
                self.cache['collation'] = self.parse('collation')
        return self.cache['collation']

    @property
    def port(self) -> int:
        if 'port' not in self.cache:
            if 'port' not in self.data:
                self.cache['port'] = 3306
            else:
                self.cache['port'] = self.parse('port')
        return self.cache['port']

    @property
    def ssh_target(self) -> Optional[Instance]:
        if self.service.task_definition.is_fargate():
            return self.service.ssh_target
        return self.cluster.ssh_target

    @property
    def ssh_targets(self) -> Sequence[Instance]:
        return self.service.cluster.ssh_targets

    @property
    def service(self) -> Service:
        if 'service' not in self.cache:
            config = get_config()
            data = config.get_section_item('services', self.data['service'])
            # We don't need the live service; we just need the service's cluster to exist
            self.cache['service'] = Service.new(data, 'deployfish')
        return self.cache['service']

    @service.setter
    def service(self, value: str) -> None:
        self.cache['service'] = value

    @property
    def cluster(self) -> Cluster:
        return self.service.cluster

    def create(
        self,
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        return self.objects.create(self, root_user, root_password, ssh_target=ssh_target, verbose=verbose)

    def update(
        self,
        root_user: str,
        root_password: str,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        return self.objects.update(self, root_user, root_password, ssh_target=ssh_target, verbose=verbose)

    def validate(
        self,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        return self.objects.validate(self, ssh_target=ssh_target, verbose=verbose)

    def dump(
        self,
        filename: str = None,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> Tuple[str, str]:
        return self.objects.dump(self, filename=filename, ssh_target=ssh_target, verbose=verbose)

    def load(
        self,
        filename: str,
        ssh_target: Instance = None,
        verbose: bool = False
    ) -> str:
        return self.objects.load(self, filename, ssh_target=ssh_target, verbose=verbose)

    def server_version(
        self,
        ssh_target: Instance = None,
        verbose: bool = False,
        user: str = None,
        password: str = None
    ) -> str:
        return self.objects.server_version(
            self,
            ssh_target=ssh_target,
            verbose=verbose,
            user=user,
            password=password
        )

    def show_grants(
        self,
        ssh_target: Instance = None,
        verbose: bool = False,
    ) -> str:
        return self.objects.show_grants(self, ssh_target=ssh_target, verbose=verbose)

    def render_mysql_command(self, sql: str, user: str = None, password: str = None) -> str:
        return '/usr/bin/mysql --host={host} --user={user} --password=\'{password}\' --port={port} --execute="{sql}"'.format(  # noqa:E501  # pylint:disable=line-too-long
            host=self.host,
            port=self.port,
            sql=sql,
            user=user if user else self.user,
            password=password if password else self.password
        )

    def render_for_create(    # type: ignore  # pylint:disable=arguments-differ
        self,
        root_user: str,
        root_password: str,
        version: str = None
    ) -> str:
        if not version:
            version = '8.0'
        sql = "CREATE DATABASE {} CHARACTER SET {} COLLATE {};".format(self.db, self.character_set, self.collation)
        if version == '5.6':
            sql += "grant all privileges on {}.* to '{}'@'%' identified by '{}';".format(
                self.db,
                self.user,
                self.password
            )
        else:
            sql += "create user '{}'@'%' identified with mysql_native_password by '{}';".format(
                self.user,
                self.password
            )
            sql += "grant all privileges on {}.* to '{}'@'%';".format(self.db, self.user)
        sql += "flush privileges;"
        return self.render_mysql_command(sql, user=root_user, password=root_password)

    def render_for_update(  # type: ignore  # pylint:disable=arguments-differ
        self,
        root_user: str,
        root_password: str,
        version: str = None
    ) -> str:
        if not version:
            version = '8.0'
        sql = "ALTER DATABASE {} CHARACTER SET = {};".format(self.db, self.character_set)
        sql += "ALTER DATABASE {} COLLATE = {};".format(self.db, self.collation)
        if version == '5.6':
            sql += "set password for '{}'@'%' = PASSWORD('{}');".format(self.user, self.password)
        else:
            sql += "alter user '{}'@'%' identified with mysql_native_password by '{}';".format(self.user, self.password)
        sql += "grant all privileges on {}.* to '{}'@'%';".format(self.db, self.user)
        sql += "flush privileges;"
        return self.render_mysql_command(sql, user=root_user, password=root_password)

    def render_for_dump(self) -> str:
        cmd = "/usr/bin/mysqldump --no-tablespaces --host={host} --user={user} --password='{password}' --port={port} --opt {db}".format(  # noqa:E501  # pylint:disable=line-too-long
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            db=self.db
        )
        return cmd

    def render_for_load(self) -> str:
        cmd = "/usr/bin/mysql --host={} --user={} --password='{}' --port={} {} < {{filename}} && rm {{filename}}".format(  # noqa:E501  # pylint:disable=line-too-long
            self.host,
            self.user,
            self.password,
            self.port,
            self.db
        )
        return cmd

    def render_for_validate(self) -> str:
        return self.render_mysql_command("select version(), current_date;")

    def render_for_server_version(self, user: str = None, password: str = None) -> str:
        return self.render_mysql_command("select version();", user=user, password=password)

    def render_for_show_grants(self) -> str:
        return self.render_mysql_command("show grants;")
