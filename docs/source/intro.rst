Introduction
============

.. include:: quickintro.rst

To use ``deployfish``, you

* Install ``deployfish``
* Define your tasks and services in ``deployfish.yml``
* Use ``deploy`` to start managing your tasks and services

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
