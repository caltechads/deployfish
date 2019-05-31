*****************
Advanced Features
*****************

.. contents::
    :local:

Architectural Assumptions
=========================

A few assuptions are made as to how your VPCs are structured. It is assumed
that you have a bastion host for each of your VPCs. These bastion hosts are
used to access the individual EC2 instances in your ECS clusters. We expect
these bastion hosts must also have a ``Name`` tag beginning with ``bastion*``,
like ``bastion-test``, etc.

deploy cluster
==============

The ``deploy cluster`` commands allow you to interract with the individual EC2
machines that make up your ECS cluster. It provides three subcommands,
``info``, ``run``, and ``ssh``. For many of the advanced features of
deployfish, the above assumptions have been made about your architecture that
are required for them to work.

Info
----
The ``info`` subcommand allows you to view information about the individual EC2
systems that make up your ECS cluster. For example::

    deploy cluster info test

Might return the output below::

    Instance 1
            IP: 10.0.0.1
            Type: t2.medium
            aws:autoscaling:groupName: web-test
            Environment: test
            Name: ecs.web-test.b.1
            project: infrastructure

    Instance 2
            IP: 10.0.0.2
            Type: t2.medium
            aws:autoscaling:groupName: web-test
            Environment: test
            Name: ecs.web-test.c.2
            project: infrastructure

deploy cluster run <service_name>
---------------------------------

The ``deploy cluster run`` subcommand allows you to run a command on each of
the instances of the cluster. When you run this command::

    deploy cluster run test

You will be prompted for the command to run::

    Command to run: rpm -qa|grep mysql

The command will then be run on each of the members of the cluster, returning
their output::

    Instance 1
    mysql55-5.5.56-1.17.amzn1.x86_64
    mysql-5.5-1.6.amzn1.noarch
    mysql55-libs-5.5.56-1.17.amzn1.x86_64
    mysql-config-5.5.56-1.17.amzn1.x86_64

    Instance 2
    mysql55-libs-5.5.56-1.17.amzn1.x86_64


deploy cluster ssh <service_name>
---------------------------------

The ``deploy cluster ssh`` subcommand allows you to ssh into a specific EC2
instance in your cluster::

    deploy cluster ssh test

This command will list the members of the cluster and ask which one you want to
connect to::

    Instance 1: 10.0.0.1
    Instance 2: 10.0.0.2
    Which instance to ssh to?:

In this case, you would have input either *1* or *2*. Once you've inputted the
instance, you will be connect via ssh to that instance.

deploy ssh <service_name>
=========================

The ``deploy ssh`` command will connect you via SSH to a system in your ECS
cluster. If you have any running containers, it will choose one of those,
otherwise it will connect to a random one. This is useful for debugging::

    deploy ssh test

deploy exec <service_name>
==========================

The ``deploy exec`` command will connect you to a running container, similar to
connecting to the host running the container and running::

    docker exec -it <contianer_id> /bin/bash

It will choose a random container. The command in our case would be::

    deploy exec test


deploy parameters 
=================

External parameter definitions in your service ``config:`` block look like this::

    config:
      - foo.bar.*
      - bar.baz.BARNEY

Such a definition tells deployfish that you want to use those parameters from AWS SSM Parameter Store in your service,
but you don't want deployfish to manage them via the ``deploy config`` set of subcommands.  You might do this if you
have a common set of configuration variables that you use across many services, for example.

The ``deploy parameters`` set of commands allows you to manage those external parameters.


deploy parameters copy <from_name> <to_name>
--------------------------------------------

The ``deploy parameters copy`` command allows you to copy an existing AWS SSM Parameter Store parameter to a new one
with a different name, optionally re-encrypting it with a new AWS KMS encryption key.  Examples::

    deploy parameters copy foo.bar.BAZ foo.bar.BARNEY
    deploy parameters copy --new-kms-key=alias/my-new-key foo.bar.BAZ foo.bar.BARNEY

The first example will copy the value from ``foo.bar.BAZ`` to a key named ``foo.bar.BARNEY``, re-encrypting it with the
same KMS Key that was used fo ``foo.bar.BAZ``.  The second example does the same thing, but encrypts the new key with
with KMS Key with alias ``alias/my-new-key``.  You can use KMS key ARNs there, too.

Wildcards::

    deploy parameters copy foo.bar.* foo.baz.

This will copy the all parameters that start with ``foo.bar.`` to paramaters with the same ending, but which start with
``foo.baz.``, re-encrypting it with the same KMS Key that was used fo ``foo.bar.BAZ``.

deploy parameters update <name>
-------------------------------

The ``deploy parameters update`` command allows you to update the value of an existing parameter, 
re-encrypt the parameter with a new AWS KMS encryption key, or do both.  Examples::

    deploy parameters update --value=something foo.bar.BAZ 
    deploy parameters update --new-kms-key=alias/my-new-key foo.bar.BAZ 
    deploy parameters update --new-kms-key=alias/my-new-key --value=something foo.bar.BAZ 

The first example will update the value of ``foo.bar.BAZ`` to a "something".  The second example will re-encrypt the
value for ``foo.bar.BAZ`` with the KMS key matching ``alias/my-new-key``, and the last example will do both.

Wildcards::

    deploy parameters update --new-kms-key=alias/my-new-key foo.bar.*
    deploy parameters update --value="something" --force-multple foo.bar.*

You can use ``deploy parameters update`` with wildcards, also.  For updating values, we make you specify
``--force-multiple`` to ensure you mean to change the value of all keys.
