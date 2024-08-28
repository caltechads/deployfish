Mysql Plugin
============

``deployfish-mysql`` is a plugin that allows you to manage databases in remote MySQL servers in AWS.

* ``deploy mysql create {name}``: Create database a database and user, with appropriate ``GRANT``.
* ``deploy mysql update {name}``: Update the user's password and ``GRANT``
* ``deploy mysql validate {name}``: Validate that the username/password combination is valid
* ``deploy mysql dump {name}``: Dump MySQL databases as SQL files to local file systems.
* ``deploy mysql load {name} {filename}``: Load a local SQL file into remote MySQL databases
* ``deploy mysql show-grants {name}``: Show GRANTs for your user

``{name}`` above refers to the ``name`` of a MySQL connection from the ``mysql:`` section of
your ``deployfish.yml`` file.  See below for how the ``mysql:`` connection works.

Configure deployfish-mysql
--------------------------

First follow the instructions for installing and configuring deployfish, then
add this stanza to your ``~/.deployfish.yml`` file:

    plugin.mysql:
        enabled: true

NOTE: ``~/.deployfish.yml`` is the config file for deployfish itself.  This is different from
the ``deployfish.yml`` file that defines your services and tasks.

Instrument your deployfish.yml
------------------------------

``deployfish-mysql`` looks in your ``deployfish.yml`` file (the one with your services and
task definitions, not the ``~/.deployfish.yml`` config file for deployfish iteslf) for a
section named ``mysql``, which has definitions of mysql databases::

    mysql:
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

Entries in the ``mysql:`` section must minimally define these keys:

* ``name``: the name of the connection.  This will be used in all the ``deploy mysql`` commands as the connection name.
* ``service``: the name of a service in the ``services:`` section.  This will be used to determine which host we use to use for SSH when doing our mysql commands
* ``host``: the hostname of the remote MySQL server
* ``db``: the name of the database to work with in ``host``
* ``user``: the username of the user to use to authenticate to ``host``
* ``pass``: the password of the user to use to authenticate to ``host``

These are optional keys that you can add to your connection definition:

* ``port``: the port to connect to on the remote MySQL server.  Default: 3306
* ``character_set``: set the character set of your database to this (used for ``deploy mysql create`` and ``deploy mysql update``).  Default: ``utf8``.
* ``collation``: set the collation set of your database to this (used for ``deploy mysql create`` and ``deploy mysql update``).  Default: ``utf8_unicode_ci``.

As you can see in the examples above, you can either hard code ``host``, ``db``, ``user`` and ``password`` in or you can reference ``config`` parameters from the ``config:`` section of the definition of our service.  For the latter, ``deployfish-mysql`` will retrieve those parameters directly from AWS SSM Parameter Store, so ensure you write the service config to AWS before trying to establish a MySQL connection.
