***************
Using Terraform
***************

.. contents::
    :local:

Problem
=======

If we use `Terraform <https://www.terraform.io/>`_ to build our infrastructure
in AWS, we can use its outputs to populate the relevant portions of our
``deployfish.yml`` file.

Setup
=====

We're going to presume a more sophisticated setup with an ECS cluster, an ELB,
a task role to allow the container to have rights to other AWS services, an S3
bucket, and and RDS database.We'll also use the terraform state file that has
been uploaded to S3.

Configuration
=============

The Terraform Section
---------------------

Here's the configuration file with terraform::

    terraform:
      statefile: 's3://hello-world-remotestate-file/hello-world-terraform-state'
      lookups:
        cluster_name: 'test-cluster-name'
        load_balancer_name: 'test-elb-id'
        task_role_arn: 'iam-role-hello-world-test-task'
        rds_address: 'test-rds-address'
        app_bucket: 's3-hello-world-test-bucket'

    services:
      - name: hello-world-test
        cluster: ${terraform.cluster_name}
        count: 1
        load_balancer:
          service_role_arn: arn:aws:iam::111122223333:role/ecsServiceRole
          load_balancer_name: ${terraform.load_balancer_name}
          container_name: hello-world
          container_port: 80
        family: hello-world
        task_role_arn: ${terraform.task_role_arn}
        containers:
          - name: hello-world
            image: tutum/hello-world
            cpu: 128
            memory: 256
            ports:
              - "80"
            command: /usr/bin/supervisord
        config:
          - DB_NAME=hello_world
          - DB_USER=hello_world_u
          - DB_PASSWORD:secure=${env.DB_PASSWORD}
          - DB_HOST=${terraform.rds_address}
          - AWS_BUCKET=${terraform.app_bucket}

We first declare a ``terraform:`` section in the top-level of your
``deployfish.yml`` file. The values we define in that section are then
available as a variable in ``services:`` section definitions, in the form
``${terraform.variable_name}``. In the above config, we've defined ``cluster`` to
be ``${terraform.cluster_name}``. When we deploy, this will be automatically
converted to::

    cluster: test-cluster-name

Defining an Environment
-----------------------

We can take this a step further, though. Typically, we will use terraform to
define all of the various environments, like test and prod. We can define the
environment in our *service* definition with the *environment* parameter::

    services:
      - name: hello-world-test
        cluster: ${terraform.cluster_name}
        environment: test
        count: 1
        ...

We can then use this environmant value in our ``terraform:`` section::

    terraform:
      statefile: 's3://hello-world-remotestate-file/hello-world-terraform-state'
      lookups:
        cluster_name: '{environment}-cluster-name'
        load_balancer_name: '{environment}-elb-id'
        task_role_arn: 'iam-role-hello-world-{environment}-task'
        rds_address: '{environment}-rds-address'
        app_bucket: 's3-hello-world-{environment}-bucket'
    ...

Multiple Environments
^^^^^^^^^^^^^^^^^^^^^

This section can then be used for multiple service definitions under
``services:`` based on the different environments::

    terraform:
      statefile: 's3://hello-world-remotestate-file/hello-world-terraform-state'
      lookups:
        cluster_name: '{environment}-cluster-name'
        load_balancer_name: '{environment}-elb-id'
        task_role_arn: 'iam-role-hello-world-{environment}-task'
        rds_address: '{environment}-rds-address'
        app_bucket: 's3-hello-world-{environment}-bucket'

    services:
      - name: hello-world-test
        cluster: ${terraform.cluster_name}
        environment: test
        count: 1
        load_balancer:
          service_role_arn: arn:aws:iam::111122223333:role/ecsServiceRole
          load_balancer_name: ${terraform.load_balancer_name}
          container_name: hello-world
          container_port: 80
        family: hello-world
        task_role_arn: ${terraform.task_role_arn}
        containers:
          - name: hello-world
            image: tutum/hello-world
            cpu: 128
            memory: 256
            ports:
              - "80"
            command: /usr/bin/supervisord
        config:
          - DB_NAME=hello_world
          - DB_USER=hello_world_u
          - DB_PASSWORD:secure=${env.DB_PASSWORD}
          - DB_HOST=${terraform.rds_address}
          - AWS_BUCKET=${terraform.app_bucket}

      - name: hello-world-prod
        cluster: ${terraform.cluster_name}
        environment: prod
        count: 1
        load_balancer:
          service_role_arn: arn:aws:iam::111122223333:role/ecsServiceRole
          load_balancer_name: ${terraform.load_balancer_name}
          container_name: hello-world
          container_port: 80
        family: hello-world
        task_role_arn: ${terraform.task_role_arn}
        containers:
          - name: hello-world
            image: tutum/hello-world
            cpu: 256
            memory: 512
            ports:
              - "80"
            command: /usr/bin/supervisord
        config:
          - DB_NAME=hello_world
          - DB_USER=hello_world_u
          - DB_PASSWORD:secure=${env.DB_PASSWORD}
          - DB_HOST=${terraform.rds_address}
          - AWS_BUCKET=${terraform.app_bucket}

Here we defined both a *test* and *prod* environment. When we deploy *test* we
will use one environment file to set the *config* parameters that contains the
*test* values, and a *prod* environment file to define its values.

Another advantage of specifying an envieronment, is that you can use this
environment in place of the service name when calling ``deploy``.

Deploy
======

To set the AWS Parameter Store values for *test*::

    deploy --env_file=test.env config write test

Then for *prod*::

    deploy --env_file=prod.env config write prod

The services are then created with::

    deploy create test

and::

    deploy create prod
