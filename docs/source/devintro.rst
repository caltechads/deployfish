************
Introduction
************

deployfish has a modular architecture that allows you to add subcommands that
have access to the internal objects through the *deployfish* library. As an
example, you can look at `deployfish-mysql <https://github.com/caltechads/deployfish-mysql>`_.

To get started, you'll need to create a new `Click <http://click.pocoo.org>`_
command group::

    import click
    import os

    from deployfish.cli import cli
    from deployfish.aws.ecs import Service
    from deployfish.config import Config, needs_config

    @cli.group(short_help="Manage a remote MySQL database")
    def mysql():
        pass

You can then add commands to that group::

    @mysql.command('create', short_help="Create database and user")
    @click.pass_context
    @click.argument('service_name')
    @needs_config
    def create(ctx, service_name):
        service = Service(service_name, config=ctx.obj['CONFIG'])

        host, name, user, passwd, port = _get_db_parameters(service)
        root = click.prompt('DB root user')
        rootpw = click.prompt('DB root password')

        cmd = "/usr/bin/mysql --host={} --user={} --password={} --port={} --execute=\"create database {}; grant all privileges on {}.* to '{}'@'%' identified by '{}';\"".format(host, root, rootpw, port, name, name, user, passwd)

        success, output = service.run_remote_script([cmd])
        print success, output

As you can see, you have full access to the `Service` class.

To register your commands with *deployfish*, you'll add an `entry_points` entry
in your `setup.py` file::

    entry_points={
        'deployfish.command.plugins': [
            'mysql = deployfish_mysql.mysql'
        ]
    },

Then install your library with `pip`.
