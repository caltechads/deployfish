***************
Parameter Store
***************

.. contents::
    :local:

Problem
=======

Most applications need some configuration. Some configuration can be passed as environment variables, but what about passwords and other secrets? Do you want them listed in the config file? These would then be visible to anyone who had access to your version control system. Any developer would also see all of them, including the production passwords. AWS introduced `Parameter Store <http://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html>`_ as part of `Systems Manager <https://aws.amazon.com/ec2/systems-manager/>`_. This allows us to store encrypted passwords and other secrets.

Setup
=====

We'll start with the same setup as the initial tutorial, just an ECS cluster.

Configuration
=============

Here's the configuration for this service::

    services:
      - name: hello-world-test
        cluster: hello-world-cluster
        count: 1
        family: hello-world
        containers:
          - name: hello-world
            image: tutum/hello-world
            cpu: 128
            memory: 256
        config:
          - VAR1=value1
          - VAR2=value2
          - PASSWORD1:secure=password1
          - PASSWORD2:secure=password2

The new parameter here is *config*:

*config*
    This is a list of values, so each begins with a dash. For an unencrypted value, it is in the form::

        - VARIABLE=VALUE

    For an encrypted value, you must add the *secure* flag::

        - VARIABLE:secure=VALUE

    In this format, the encrypted value will be encrypted with the default key. For better security, make a unique key for each app and specify it in this format::

        - VARIABLE:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=VALUE

For more information about creating keys, see `AWS Key Management Service (KMS) <https://aws.amazon.com/kms/>`_.

Managing Config Parameters
--------------------------

In addition to deploying your services, you can also manage your config with *deployfish* using the *config* subcommand.

To view your current config in AWS, run::

    deploy config show hello-world-test

To save config to AWS, run::

    deploy config write hello-world-test

Reading From The Environment
----------------------------

You might have noticed that so far this solution is still displaying passwords in the *deployfish.yml* file for all the developers to see. This is not a good security practice as we've mentioned. The best way to deal with this is to have the secret parameter values defined in an environment variable. You would then change the *config* section to be::

    ...
    config:
      - VAR1=value1
      - VAR2=value2
      - PASSWORD1:secure=${env.PASSWORD1}
      - PASSWORD2:secure=${env.PASSWORD2}

To make this easier, *deployfish* allows you to pass an environment file on the command line::

    deploy --env_file=config.env create hello-world-test

This file is expected to be in the format::

    VARIABLE=VALUE
    VARIABLE=VALUE

These variables will all be loaded into the environment, so available to read from the *config* parameters. You would typically use a different file for each service.

You can also specify this file in the *service* definition itself::

    services:
      - name: hello-world-test
        cluster: hello-world-cluster
        count: 1
        family: hello-world
        env_file: config.env
        ...

Using Config Parameters
-----------------------

So now that we have all of these values loaded into the AWS Parameter Store, how do we use them? We've included a subcommand in *deployfish* called *entrypoint*. You would define this as your *entrypoint* in your *Dockerfile*::

    ENTRYPOINT ["deploy", "entrypoint"]

You would have to install *deployfish* in your container for this to work.

With this as your *entrypoint*, you will need to set the *command* parameter of the *container* to be your original *entrypoint*::

    ...
    containers:
      - name: hello-world
        image: tutum/hello-world
        cpu: 128
        memory: 256
        command: /usr/bin/supervisord
    ...

The *entrypoint* that is run will then be::

    deploy entrypoint <command>

or in this case::

    deploy entrypoint /usr/bin/supervisord

When this is run, your defined *config* parameters will be downloaded from AWS Parameter Store and defined locally as environment variables, which you will then access as you would any environment variable.

If you run your docker container locally, the *entrypoint* subcommand will simply call the command without downloading anything from AWS Parameter Store. You would then use locally defined environment variables to set the various parameter values.
