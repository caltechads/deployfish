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
