Introduction
============

``deployfish`` has commands for managing the whole lifecycle of your application:

* Create, update, destroy and restart ECS services
* Manage multiple environments for your service (test, qa, prod, etc.)
* View the configuration and status of running ECS services
* Scale the number of containers in your service, optionally scaling its
  associated autoscaling group at the same time
* Run a one-off command related to your service

Additionally, ``deployfish`` integrates with
`terraform <https://www.terraform.io>`_ state files so that you can use the
values of terraform outputs directly in your ``deployfish`` configurations.

To use ``deployfish``, you

* Install ``deployfish``
* Define your service in ``deployfish.yml``
* Use ``deploy`` to start managing your service

A simple ``deployfish.yml`` looks like this::

    services:
      - name: my-service
        environment: prod
        cluster: my-cluster
        count: 2
        load_balancer:
          service_role_arn: arn:aws:iam::123142123547:role/ecsServiceRole
          load_balancer_name: my-service-elb
          container_name: my-service
          container_port: 80
        family: my-service
        network_mode: bridge
        task_role_arn: arn:aws:iam::123142123547:role/myTaskRole
        containers:
          - name: my-service
            image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/my-service:0.0.1
            cpu: 128
            memory: 256
            ports:
              - "80"
            environment:
              - ENVIRONMENT=prod
              - ANOTHER_ENV_VAR=value
              - THIRD_ENV_VAR=value

See the ``examples/`` folder in this repository for example ``deployfish.yml``
files.
