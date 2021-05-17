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

    deploy cluster info web-test

Might return the output below::

    Cluster: web-test
      pk                  :     web-test
      name                :     web-test
      arn                 :     arn:aws:ecs:us-west-2:123456789012:cluster/web-test
      status              :     ACTIVE
      instances           :     6
      autoscaling_group   :     web-test
      task counts
          running           :     5
          pending           :     0

    Container instances
    -------------------

    Name              Instance Type    IP Address      Free CPU    Free Memory
    ----------------  ---------------  ------------  ----------  -------------
    ecs.web-test.b.2  t2.medium        10.0.1.1           768            102
    ecs.web-test.b.1  t2.medium        10.0.1.2          1536            182
    ecs.web-test.c.2  t2.medium        10.0.2.1          1408           1206
    ecs.web-test.c.1  t2.medium        10.0.2.2          1024            614

    Services
    --------

    Name                       Version      Desired    Running  Created
    -------------------------  ---------  ---------  ---------  -------------------
    service1                   2.0.8              2          2  2021-04-02 17:29:30
    service2                   1.4.1              1          1  2021-04-23 11:21:39
    service3                   2.1.2              2          2  2020-08-19 09:33:12


deploy service ssh <service_name>
=================================

The ``deploy service ssh`` command (alias: ``deploy ssh``) will connect you via SSH to a system in your ECS cluster. If
you have any running containers, it will choose one of those, otherwise it will connect to a random one. This is useful
for debugging::

    # ssh to a container instance for the service identified by environment "test' in deployfish.yml
    deploy service ssh test
    # ssh to a container instance for the service "service1" in cluster "web-test"
    deploy service ssh web-test:service1

deploy service exec <service_name>
==================================

The ``deploy service exec`` command (alias: ``deploy exec``) will connect you to a running container, similar to
connecting to the host running the container and running::

    docker exec -it <contianer_id> /bin/bash

It will choose a random container. The command in our case would be::

    # exec into a container for the service identified by environment "test' in deployfish.yml
    deploy service exec test
    # exec into a container for the service "service1" in cluster "web-test"
    deploy service exec web-test:service1
