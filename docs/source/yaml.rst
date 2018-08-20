************************
deployfish.yml Reference
************************

..
    .. contents::

The deployfish service config file is a YAML file defining ECS services, task
definitions and one-off tasks associated with those services.

* The default path for a deployfish configuration file is ``./deployfish.yml``.
* If the environment variable ``DEPLOYFISH_CONFIG_FILE`` is defined, ``deployfish``
  will use that instead.
* If you pass a filename to ``deploy`` with the ``-f`` or ``--filename`` command line
  flag, that will be used even if ``DEPLOYFISH_CONFIG_FILE`` is defined.

Options specified in the Dockerfile for your containers (e.g., ``ENTRYPOINT``,
``CMD``, ``ENV``) are respected by default - you don’t need to specify them again
in ``deployfish.yml``.

You can use terraform outputs in configuration values with a
``${terraform.<key>}`` syntax - see the Interpolation_ section for full details.

You can also use the values of environment variables in configuration values with a
``${env.<key>}`` syntax - see the Interpolation_ section for full details.


AWS Credentials
===============

deployfish uses `boto3 <https://boto3.readthedocs.io>`_ to do all its work in
AWS and by default defers to boto3 credential resolution to figure out what
AWS credentials it should use.  See `Configuring Credentials <https://boto3.readthedocs.io/en/latest/guide/configuration.html#guide-configuration)>`_
in boto3's documentation for details.

Alternately, you can tell deployfish specifically how to get your AWS credentials by
defining an ``aws:`` section in ``deployfish.yml``.

.. note::

  The ``deploy entrypoint`` command will ignore any ``aws:`` section in
  ``deployfish.yml`` We're assuming that you're only ever running ``deploy
  entrypoint`` inside a container in your AWS service.  It should get its
  credentials from the container's IAM ECS Task Role.

Static credentials
------------------

Static credentials can be provided by adding an ``access_key`` and ``secret_key``
in-line in an ``aws:`` section in ``deployfish.yml``.

Usage::

    aws:
      access_key: anaccesskey
      secret_key: asecretkey
      region: us-west-2

If you specify static credentials in this way, they will be used instead of any
credentials found in your environment.  ``region`` here is optional.

Using a profile from your AWS credentials file
----------------------------------------------

You can use an AWS credentials file to specify your credentials and then set up
your ``aws:`` section to use credentials from a particular profile. The default
location is ``$HOME/.aws/credentials`` on Linux and OS X.  You can specify a
different location for this file via the ``AWS_SHARED_CREDENTIALS_FILE``
environment variable.

Usage::

    aws:
      profile: customprofile
      region: us-west-2


``region`` here is optional.

ECS Service Definition
======================

This section contains a list of all configuration options supported by a
ECS Service definition in version 1.

Services are specified in a YAML list under the top level ``services:`` key like
so::

    services:
      - name: foobar-prod
        ...
      - name: foobar-test
        ...


name
----

(String, Required) The name of the actual ECS service.  ``name`` is required.
The restrictions on characters in ECS services are in play here:  Up to 255
letters (uppercase and lowercase), numbers, hyphens, and underscores are
allowed.

Once your service has been created, this is not changable without deleting and
re-creating the service. ::

    services:
      - name: foobar-prod

cluster
-------

(String, Required) The name of the actual ECS cluster in which we'll create our service. ``cluster``
is required. This has to exist in AWS before running ``deploy create
<service-name>``. ::

    services:
      - name: foobar-prod
        cluster: foobar-cluster

environment
-----------

(String, Optional) This is a keyword that can be used in terraform lookups (see
"Interpolation_", below).  It can also be used as an alias for the service name in the ``deploy`` command. ::

    services:
      - name: foobar-prod
        environment: prod

scheduling_strategy
-------------------

(String, Optional) When we create the ECS service, configure the service to run in REPLICA or DAEMON. Default to REPLICA. ::

    services:
      - name: foobar-prod
        clsuter: foodbar-cluster
        scheduling_strategy: DAEMON

count
-----

(Integer, Required for REPLICA) When we create the ECS service, configure the service to run this many tasks. ::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2

``count`` is only meaningful at service creation time.  To change the count in an
already created service, use ``deploy scale <service_name> <count>``

maximum_percent
---------------

(Integer, Optional) This is the upper limit on the number of tasks
that are allowed in the RUNNING or PENDING state during a deployment, as a percentage of the ``count``.
This must be configured along with ``minimum_healthy_percent``. If not provided will default to 200. If schdeuling strategy is set to DAMEON, it will be fixd at 100 ::

    services:
      - name: foobar-prod
        maximum_percent: 200

See `Service Definition Parameters <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service_definition_parameters.html)>`_.

minimum_healthy_percent
---------------

(Integer, Optional) ECS service, this is the lower limit on the number of tasks
that must remain in the RUNNING state during a deployment, as a percentage of the ``count``. This must be configured
along with ``maximum_percent``. If not provided will default to 0. ::

    services:
      - name: foobar-prod
        minimum_healthy_percent: 50

See `Service Definition Parameters <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service_definition_parameters.html)>`_.

placement_constraints
-----------

(Optional) An array of placement constraint objects to use for tasks in your service. You can specify a maximum of 10 constraints per task (this limit includes constraints in the task definition and those specified at run time).

    services:
         - name: foobar-prod
           placement_constraints:
            - type: distinctInstance
            - type: memberOf
              expression: 'attribute:ecs.instance-type =~ t2.*'

See `Service Definition Parameters <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service_definition_parameters.html)>`_.

placement_strategy
-----------

(Optional) The placement strategy objects to use for tasks in your service. You can specify a maximum of four strategy rules per service.

    services:
         - name: foobar-prod
           placement_strategy:
            - type: random
            - type: spread
              field: 'attribute:ecs.availability-zone'

See `Service Definition Parameters <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service_definition_parameters.html)>`_.

launch_type
-----------

(Required for Fargate tasks)

If you are configuring a Fargate task you must specify the launch type as ``FARGATE``, otherwise
the default value of ``EC2`` is used.

The Fargate launch type allows you to run your containerized applications without the need to
provision and manage the backend infrastructure. Just register your task definition and Fargate
launches the container for you.

If you use the Fargate launch type, the following task parameters are not valid:

* ``dockerSecurityOptions``
* ``links``
* ``linuxParameters``
* ``placementConstraints``
* ``privileged``

Example::

    services:
      - name: foobar-prod
        launch_type: FARGATE

See `Amazon ECS Launch Types <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/launch_types.html)>`_.

vpc_configuration
-----------------

(Required for Fargate tasks)

If you are configuring a Fargate task, you have to specify your vpc configuration at the task level.

deployfish won't create the vpc, subnets or security groups for you --
you'll need to create it before you can use ``deploy create <service_name>``

You'll need to specify

* ``subnets``: (array) The subnets in the VPC that the task scheduler should consider for placement.
  Only private subnets are supported at this time. The VPC will be determined by the subnets you
  specify, so if you specify multiple subnets they must be in the same VPC.
* ``security_groups``: (array) The ID of the security group to associate with the service.
* ``public_ip``: (string) Whether to enabled or disable public IPs. Valid Values are ``ENABLED`` or ``DISABLED``

Example::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        vpc_configuration:
          subnets:
            - subnet-12345678
            - subnet-87654321
          security_groups:
            - sg-12345678
          public_ip: ENABLED


autoscalinggroup_name
---------------------

(Optional)

If you have a dedicated Autoscaling Group for your service, you can declare it
with the ``autoscalinggroup_name`` option.  This will allow you to scale the ASG
up and down when you scale the service up and down with ``deploy scale
<service-name> <count>``.

deployfish won't create the autoscaling group for you --
you'll need to create it before you can use ``deploy scale <service_name>
<count>`` to manipulate it. ::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        autoscalinggroup_name: foobar-asg

load_balancer
-------------

(Optional)

If you're going to use an ELB or an ALB with your service, configure it with a
``load_balancer`` block.

The load balancer info for the service can't be changed after the service has
been created.  To change any part of the load balancer info, you'll need to
destroy and recreate the service.

ELB
^^^

To specify that the the service is to use an ELB, you'll need to specify

* ``service_role_arn``: (string) The name or full ARN of the IAM role that allows
  ECS to make calls to your load balancer on your behalf.
* ``load_balancer_name``: (string) The name of the ELB.
* ``container_name``: (string) the name of the container to associate with the
  load balancer
* ``container_port``: (string) the port on the container to associate with the
  load balancer.  This port must correspond to a container port on container
  ``container_name`` in your service's task definition

Example::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        load_balancer:
          service_role_arn: arn:aws:iam::123142123547:role/ecsServiceRole
          load_balancer_name: foobar-prod-elb
          container_name: foobar-prod
          container_port: 80

deployfish won't create the load balancer for you --
you'll need to create it before running ``deploy create <service_name>``.


ALB
^^^

To specify that the the service is to use an ALB, you'll need to specify

* ``service_role_arn``: (string) The name or full ARN of the IAM role that allows
  ECS to make calls to your load balancer on your behalf.
* ``target_group_arn``: (string) The full ARN of the target group to use for this service.
* ``container_name``: (string) the name of the container to associate with the
  load balancer
* ``container_port``: (string) the port on the container to associate with the
  load balancer.  This port must correspond to a container port on container
  ``container_name`` in your service's task definition

deployfish won't create the target group for you == you'll need to create it
before running ``deploy create <service_name>``.

Example::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        load_balancer:
          service_role_arn: arn:aws:iam::123142123547:role/ecsServiceRole
          target_group_arn: foobar-prod-elb
          container_name: foobar-prod
          container_port: 80

service_discovery
-----------------

(Optional)

If you're going to use ECS service discovery, configure it with a ``service_discovery``
block.

The service discovery info for the service can't be changed after the service has
been created. To change any part of the service discovery info, you'll need to destroy
and recreate the service.

To use service discovery you'll need to specify

* ``namespace``: (string) The service discovery namespace that the new service will
  be associated with.
* ``name``: (string) The name of the service discovery service
* ``dns_records``: (list) A list of DNS records the service discovery service should create
    * ``type``: (string) The type of dns record. Valid values are ``A`` and ``SRV``.
    * ``ttl``: (int) The ttl of the dns record.

Example::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        service_discovery:
          namespace: local
          name: foobar-prod
          dns_records:
            type: A
            ttl: 10

This would create a new service discovery service on the ``local`` Route53 private zone. The DNS would be
``foobar-prod.local``

See `Amazon ECS Service Discovery <https://aws.amazon.com/blogs/aws/amazon-ecs-service-discovery/)>`_.

application_scaling
-------------------

(Optional)

If you want your service so scale up and down with service CPU, configure it
with an ``application_scaling`` block.

Example::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        application_scaling:
            min_capacity: 2
            max_capacity: 4
            role_arn: arn:aws:iam::123445678901:role/ApplicationAutoscalingECSRole
            scale-up:
                cpu: ">=60"
                check_every_seconds: 60
                periods: 5
                cooldown: 60
                scale_by: 1
            scale-down:
                cpu: "<=30"
                check_every_seconds: 60
                periods: 30
                cooldown: 60
                scale_by: -1

This block says that, for this service:

* There should be a minimum of 2 tasks and a maximum of 4 tasks
* ``arn:aws:iam::123445678901:role/ApplicationAutoscalingECSRole`` grants permission to start
  new containers for our service
* Scale our service up by one task if ECS Service Average CPU is greater
  than 60 percent for 300 seconds.  Don't scale up more than once every 60
  seconds.
* Scale our service down by one task if ECS Service Average CPU is less
  than or equal to 30 percent for 1800 seconds.  Don't scale down more than
  once every 60 seconds.


min_capacity
^^^^^^^^^^^^

(Integer, Required) The minimum number of tasks that should be running in
our service.

max_capacity
^^^^^^^^^^^^

(Integer, Required) The maximum number of tasks that should be running in
our service.  Note that you should ensure that you have enough resources in
your cluster to actually run this many of your tasks.

role_arn
^^^^^^^^

(String, Required) The name or full ARN of the IAM role that allows Application
Autoscaling to muck with your service.  Your role definition should look like
this::

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "application-autoscaling.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }

And it needs an appropriate policy attached.  The below policy allows the
role to act on any service. ::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Stmt1456535218000",
                "Effect": "Allow",
                "Action": [
                    "ecs:DescribeServices",
                    "ecs:UpdateService"
                ],
                "Resource": [
                    "*"
                ]
            },
            {
                "Sid": "Stmt1456535243000",
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:DescribeAlarms"
                ],
                "Resource": [
                    "*"
                ]
            }
        ]
    }

See `Amazon ECS Service Auto Scaling IAM Role <http://docs.aws.amazon.com/AmazonECS/latest/developerguide/autoscale_IAM_role.html)>`_.

scale-up, scale-down
^^^^^^^^^^^^^^^^^^^^

(Required) You should have exactly two scaling rules sections, and they should
be named precisely ``scale-up`` and ``scale-down``.

cpu
^^^

(String, Required) What CPU change causes this rule to be activated?  Valid
operators are: ``<=``, ``<``, ``>``, ``>=``.  The CPU value itself is a float.

You'll need to put quotes around your value of ``cpu``, else the YAML parser will
freak out about the ``=`` sign.

check_every_seconds
^^^^^^^^^^^^^^^^^^^

(Integer, Required) Check the Average service CPU every this many seconds.

periods
^^^^^^^

(Integer, Required) The ``cpu`` test must be true for ``check_every_seconds *
periods`` seconds for scaling to actually happen.

scale_by
^^^^^^^^

(Integer, Required) When it's time to scale, scale by this number of tasks.  To
scale up, make the number positive; to scale down, make it negative.

cooldown
^^^^^^^^

(Integer, Required) The amount of time, in seconds, after a scaling activity
completes where previous trigger-related scaling activities can influence
future scaling events.

See "Cooldown" in AWS' `PutScalingPolicy <https://docs.aws.amazon.com/ApplicationAutoScaling/latest/APIReference/API_PutScalingPolicy.html>`_ documentation.


family
------

(String, Required) When we create task definitions for this service, put them
in this family.  When you go to the "Task Definitions" page in the AWS web
console, what is listed under "Task Definition" is the family name. ::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        family: foobar-prod-task-def


See also the `AWS documentation <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#family>`_.

network_mode
------------

(String, Optional) The Docker networking mode for the containers in our task.
One of: ``bridge``, ``host``, ``awsvpc`` or ``none``. If this parameter is omitted, a service is assumed to
use ``bridge`` mode. ::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        family: foobar-prod-task-def
        network_mode: bridge

See the `AWS documentation <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#network_mode>`_ for
what each of those modes are.

task_role_arn
-------------

(String, Optional) A task role ARN for an IAM role that allows the containers in the task
permission to call the AWS APIs that are specified in its associated policies
on your behalf. ::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        family: foobar-prod-task-def
        network_mode: bridge
        task_role_arn: arn:aws:iam::123142123547:role/my-task-role

deployfish won't create the Task Role for you -- you'll need to create it
before running ``deploy create <service_name>``.

See also the `AWS documentation <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#task_role_arn>`_, and
`IAM Roles For Tasks <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html>`_

execution_role_arn
------------------

(String, Required for Fargate) A task exeuction role ARN for an IAM role that allows Fargate to pull container images and publish container logs
to Amazon CloudWatch on your behalf.::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        family: foobar-prod-task-def
        network_mode: bridge
        execution_role_arn: arn:aws:iam::123142123547:role/my-task-role

deployfish won't create the Task Execution Role for you -- you'll need to create it
before running ``deploy create <service_name>``.

See also the `IAM Roles For Tasks <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html>`_

cpu
---

(Required for Fargate tasks)

If you are configuring a Fargate task, you have to specify the cpu at the task level, and there are specific values
for cpu which are supported which we describe below.

------------------
 CPU value
------------------
 256 (.25 vCPU)
 512 (.5 vCPU)
 1024 (1 vCPU)
 2048 (2 vCPU)
 4096 (4 vCPU)

See also the `Task Definition Parameters <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#task_size>`_

memory
------

(Required for Fargate tasks)

If you are configuring a Fargate task, you have to specify the memory at the task level, and there are specific values
for memory which are supported which we describe below.

-------------------------------------------------------------------------------------
 Memory value (MiB)
-------------------------------------------------------------------------------------
 512 (0.5GB), 1024 (1GB), 2048 (2GB)
 1024 (1GB), 2048 (2GB), 3072 (3GB), 4096 (4GB)
 2048 (2GB), 3072 (3GB), 4096 (4GB), 5120 (5GB), 6144 (6GB), 7168 (7GB), 8192 (8GB)
 Between 4096 (4GB) and 16384 (16GB) in increments of 1024 (1GB)
 Between 8192 (8GB) and 30720 (30GB) in increments of 1024 (1GB)

See also the `Task Definition Parameters <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#task_size>`_

Container Definitions
=====================

Define your containers within a service by using a ``containers:`` subsection.

``containers`` is a list of containers like so::

    services:
      - name: foobar-prod
        cluster: foobar-cluster
        count: 2
        containers:
          - name: foo
            image: my_repository/foo:0.0.1
            cpu: 128
            memory: 256
          - name: bar
            image: my_repository/baz:0.0.1
            cpu: 256
            memory: 1024

Each of the containers listed in the ``containers`` list will be added to the
task definition for the service.

For each of the following attributes, see also the `AWS
documentation <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#standard_container_definition_params>`_.

**NOTE**: Each container in your service automatically gets their log
configuration setup as 'fluentd', with logs being sent to ``127.0.0.1:24224`` and
being tagged with the name of the container.

name
----

(String, Required) The name of the container. If you are linking multiple
containers together in a task definition, the name of one container can be
entered in the links of another container to connect the containers.  The
restrictions on characters in ECS container are in play here:  Up to 255
letters (uppercase and lowercase), numbers, hyphens, and underscores are
allowed. ::

    containers:
      - name: foo

image
-----

(String, Required) The image used to start the container. Up to 255 letters
(uppercase and lowercase), numbers, hyphens, underscores, colons, periods,
forward slashes, and number signs are allowed.

For an AWS ECR repository::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1


For a Docker hub repository::

    containers:
      - name: foo
        image: centos:7

memory
------

(Integer, Required) The hard limit of memory (in MB) available to the container.  If
the container tries to exceed this amount of memory, it is killed. ::

    containers:
      - name: foo
        image: centos:7
        memory: 512

memoryReservation
-----------------

(Integer, Optional) The soft limit (in MB) of memory to reserve for the
container. When system memory is under heavy contention, Docker attempts to
keep the container memory to this soft limit; however, your container can
consume more memory when it needs to, up to the hard limit specified
with the ``memory`` parameter.  ``memoryReservation`` must be less than
``memory`` ::

    containers:
      - name: foo
        image: centos:7
        memory: 512
        memoryReservation: 256

For example, if your container normally uses 128 MiB of memory, but
occasionally bursts to 256 MiB of memory for short periods of time, you can set
a memoryReservation of 128 MiB, and a memory hard limit of 300 MiB. This
configuration would allow the container to only reserve 128 MiB of memory from
the remaining resources on the container instance, but also allow the container
to consume more memory resources when needed.

cpu
---

(Integer, Required) The number of cpu units to reserve for the container. A
container instance has 1,024 cpu units for every CPU core. ::

    containers:
      - name: foo
        image: centos:7
        cpu: 128

ports
-----

(List of strings, Optional) A list of port mappings for the container.

Either specify both ports (HOST:CONTAINER), or just the container port (a
random host port will be chosen).  You can also specify a protocol as
(HOST:CONTAINER/PROTOCOL).  Note that both HOST and CONTAINER here must be
single ports, not port ranges as ``docker-compose.yml`` allows in its port
definitions.  PROTOCOL must be one of 'tcp' or 'udp'.  If no PROTOCOL is
specified, we assume 'tcp'. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        ports:
         - "80"
         - "8443:443"
         - "8125:8125/udp"

links
-----

(List of strings, Optional) A list of names of other containers in
our task definition.  Adding a container name to links allows
containers to communicate with each other without the need for
port mappings.

Links should be specified as ``CONTAINER_NAME``, or ``CONTAINER_NAME:ALIAS``. ::

    containers:
      - name: my-service
        image: 123445564666.dkr.ecr.us-west-2.amazonaws.com/my-service:0.1.0
        cpu: 128
        memory: 256
        links:
          - redis
          - db:database
      - name: redis
        image: redis:latest
        cpu: 128
        memory: 256
      - name: db
        image: mysql:5.5.57
        cpu: 128
        memory: 512
        environment:
            MYSQL_ROOT_PASSWORD: __MYSQL_ROOT_PASSWD__

essential
---------

(Boolean, Optional) If the essential parameter of a container is marked as
true, and that container fails or stops for any reason, all other containers
that are part of the task are stopped. If the essential parameter of a
container is marked as false, then its failure does not affect the rest of the
containers in a task. If this parameter is omitted, a container is assumed to
be essential. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        essential: true
      - name: bar
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        essential: false

extra_hosts
-----------

(list of strings, Optional) Add hostname mappings. ::

    containers:
      - name: foo
        extra_hosts:
        - "somehost:162.242.195.82"
        - "otherhost:50.31.209.229"

An entry with the ip address and hostname will be created in ``/etc/hosts`` inside
containers for this service, e.g::

    162.242.195.82  somehost
    50.31.209.229   otherhost

entrypoint
----------

(String, Optional) The entry point that is passed to the container.  Specify it
as a string and Deployintaor will split the string into an array for you for
passing to ECS. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        entrypoint: /entrypoint.sh here are arguments

command
-------

(String, Optional) The command that is passed to the container.  Specify it
as a string and Deployintaor will split the string into an array for you for
passing to ECS. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        command: apachectl -DFOREGROUND

environment
-----------

(Optional) Add environment variables. You can use either an array or a
dictionary. Any boolean values; true, false, yes no, need to be enclosed in
quotes to ensure they are not converted to True or False by the YML parser. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        environment:
          DEBUG: 'True'
          ENVIRONMENT: prod
          SECERTS_BUCKET_NAME: my-secrets-bucket
      - name: bar
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        environment:
          - DEBUG=True
          - ENVIRONMENT=prod
          - SECERTS_BUCKET_NAME=my-secrets-bucket

ulimits
-------

(Optional) Override the default ulimits for a container. You can either specify
a single limit as an integer or soft/hard limits as a mapping. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        ulimits:
          nproc: 65535
          nofile:
            soft: 65535
            hard: 65535

dockerLabels
------------

(Optional) Add metadata to containers using Docker labels. You can use either
an array or a dictionary.

Use reverse-DNS notation to prevent your labels from conflicting with those
used by other software. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        dockerLabels:
        labels:
          edu.caltech.description: "Fun webapp"
          edu.caltech.department: "Dept. of Redundancy Dept."
          edu.caltech.label-with-empty-value: ""
      - name: bar
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        dockerLabels:
          - "edu.caltech.description=Fun webapp"
          - "edu.caltech.department=Dept. of Redundancy Dept."
          - "edu.caltech.label-with-empty-value"

volumes
-------

(List of strings, Optional) Specify a path on the host machine
(HOST:CONTAINER), or an access mode (HOST:CONTAINER:ro).  The HOST
and CONTAINER paths should be absolute paths. ::

    containers:
      - name: foo
        image: 123142123547.dkr.ecr.us-west-2.amazonaws.com/foo:0.0.1
        dockerLabels:
        volumes:
          - /host/path:/container/path
          - /host/path-ro:/container/path-ro:ro

logging
-------

(String and dictionary, Optional) Specify a log driver and its associated options.

To configure awslogs::

    logging:
      driver: awslogs
      options:
        awslogs-group: awslogs-mysql
        awslogs-region: ap-northeast-1
        awslogs-stream-prefix: awslogs-example

For fluentd::

    logging:
      driver: fluentd
      options:
        fluentd-address: 127.0.0.1:24224
        tag: hello


**NOTE**: if you don't provide a ``logging:`` section, no logs will be emitted
from your service.

Secrets Management with AWS Parameter Store
===========================================

The ``config:`` subsection of an ECS service is a list of parameters that are
stored in the `AWS Parameter Store <http://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html>`_
as part of `Systems Manager <https://aws.amazon.com/ec2/systems-manager/>`_.
This allows us to store settings, encrypted passwords and other secrets without
exposing them to casual view in the AWS Console via the ``environment`` section
of the container definition.

This is a list, so each item begins with a dash. For an unencrypted value, it is in the form::

    - VARIABLE=VALUE

For an encrypted value, you must add the *secure* flag::

    - VARIABLE:secure=VALUE

In this format, the encrypted value will be encrypted with the default key. For
better security, make a unique key for each app and specify it in this format::

    - VARIABLE:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=VALUE

For more information about creating keys, see `AWS Key Management Service (KMS) <https://aws.amazon.com/kms/>`_.

Here's an example configuration::

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

Managing Config Parameters in AWS
---------------------------------

In addition to deploying your services, you manage your config with ``deploy``
using the ``config`` subcommand.

To view your current values of your config in AWS, run::

    deploy config show hello-world-test

To update the values of the config to AWS, run::

    deploy config write hello-world-test

Reading From The Environment
----------------------------

In practice, you do not want the ``deployfish.yml`` file to contain actual
passwords, so the best practice is to have the secret parameter values defined
in an environment variable. You would then change the *config* section to be::

    ...
    config:
      - VAR1=value1
      - VAR2=value2
      - PASSWORD1:secure=${env.PASSWORD1}
      - PASSWORD2:secure=${env.PASSWORD2}


See the Interpolation_ section for full details on how environment variable
replacement in ``deployfish.yml`` works.

You typically should use a different file for each service.


Loading config: variables into your container environment
---------------------------------------------------------

So now that we have all of these values loaded into the AWS Parameter Store,
how do we use them? We've included a subcommand in ``deployfish`` called
``entrypoint``. Define this as your ``entrypoint`` in your ``Dockerfile``::

    ENTRYPOINT ["deploy", "entrypoint"]

You have to install ``deployfish`` in your container for this to work.

With this as your ``entrypoint``, you will need to set the ``command`` parameter of
the container to be your original ``ENTRYPOINT``::

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

When this is run, your defined ``config`` parameters will be downloaded from AWS
Parameter Store and defined locally as environment variables, which you will
then access as you would any environment variable.

.. note::

  If you run your docker container locally, the ``entrypoint`` subcommand
  will simply call the command without downloading anything from AWS Parameter
  Store. You would then use locally defined environment variables to set the
  various parameter values.

Service Helper Tasks
====================

In the ``tasks`` section of the service defintion, you can define helper tasks
to be associated with your service and define commands on them that you can run via
``deploy run_task <service> <command>``.

The reason this exists is to enable us to run one-off or periodic
functions (migrate datbases, clear caches, update search indexes, do database
backups or restores, etc.) for our services.

Task definitions listed in the ``tasks`` list support the same configuration
options as those in the ``services`` list: ``family``, ``environment``,
``network_mode``, ``task_role_arn``, and all the same options under ``containers``.

Example
^^^^^^^

When you do a ``deploy update <service_name>``, deployfish automaticaly updates
the task definition to what is listed in the ``tasks`` entry for each task, and
adds a docker label to the first container of the task definition for the
service for each task, recording the ``<family>:<revision>`` string of the
correct task revision. ::


    services:
      - name: foobar-prod
        environment: prod
        cluster: foobar-prod-cluster
        count: 2
        load_balancer:
          service_role_arn: arn:aws:iam::123142123547:role/ecsServiceRole
          load_balancer_name: foobar-prod-elb
          container_name: foobar
          container_port: 80
        family: foobar-prod
        network_mode: bridge
        task_role_arn: arn:aws:iam::123142123547:role/myTaskRole
        containers:
          - name: foobar
            image: foobar:0.0.1
            cpu: 128
            memory: 512
            ports:
              - "80"
              - "443"
            environment:
              - ENVIRONMENT=prod
              - SECRETS_BUCKET_NAME=my-secrets-bucket
        tasks:
          - family: foobar-helper-prod
            environment: prod
            network_mode: bridge
            task_role_arn: arn:aws:iam::123142123547:role/myTaskRole
            containers:
              - name: foobar
                image: foobar:0.0.1
                cpu: 128
                memory: 256
                environment:
                  - ENVIRONMENT=prod
                  - SECRETS_BUCKET_NAME=my-secrets-bucket
            commands:
              migrate: manage.py migrate
              update_index: manage.py update_index

This example defines a task "foobar-helper-prod" for our service "foobar-prod"
and defines two available commands on that task: ``migrate`` and ``update_index``.

When you do ``deploy update foobar-prod``, deployfish will create a new
revision of the ``foobar-helper-prod`` task defintion and add a docker label to
the ``foobar-prod`` task definition of
``edu.caltech.foobar-helper-prod=foobar-helper-prod:<revision>``", where
``revision`` is the revision of ``foobar-helper-prod`` that we just created.

Then when you run ``deploy run_task foobar-prod migrate``, deployfish will:

1. Search for ``migrate`` among all the separate ``commands`` listings under ``tasks``
1. Determine that ``migrate`` belongs to the ``foobar-helper-prod`` task
1. Look on the active ``foobar-prod`` service task definition for the ``edu.caltech.foobar-helper-prod`` docker label
1. Use the value of that label to figure out which revision of our ``foobar-helper-prod`` task to run
1. Call the ECS ``RunTasks`` API call with that task revision and overriding ``CMD`` to ``manage.py migrate``


commands
--------

This is a dictionary of keys to commandline strings.  The keys are what you'll
use as ``<command>`` when doing ``deploy run_task <service-name> <command>``, and
the values are the actual command-line to use as the ``CMD`` override when
running the task.

.. _Interpolation:

Variable interpolation in deployfish.yml
========================================

You can use variable replacement in your service definitions to dynamically
replace values from two sources: your local shell environment and from a remote
terraform state file.


Environmnent variable replacement
---------------------------------

You can add ``${env.<environment var>}`` to your service definition anywhere you
want the value of the shell environment variable ``<environment var>``.  For
example, for the following ``deployfish.yml`` snippet::

    services:
      - name: foobar-prod
        environment: prod
        config:
          - MY_PASSWORD=${env.MY_PASSWORD}

``deployfish`` does not by default inherit your shell environment when doing
these ``${env.VAR}`` replacements. You must tell ``deployfish`` how you want it
to load those environment variables.

deploy --import_env command line option
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you run ``deploy`` with the ``--import_env`` option, it will import your
shell environment into the deployfish environment.  Then anything you've
defined in your shell environment will be available for ``${env.VAR}``
replacements.

Example::

    deploy --import_env <subcommand> [options]

deploy --env_file command line option
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``deploy`` also supports declaring environment variables in a file instead of
having to actually have them set in your environment.  The file should follow
these rules:

* Each line should be in ``VAR=VAL`` format.
* Lines beginning with # (i.e. comments) are ignored.
* Blank lines are ignored.
* There is no special handling of quotation marks.

Example::

    deploy --env_file=<filename> <subcommand> [options]

Then anything you've defined in ``<filename>`` defined in your shell environment
will be available for ``${env.VAR}`` replacements.


The "env_file" service definition option
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also specify this environment variable file in the ECS service
definition itself::

    services:
      - name: hello-world-test
        cluster: hello-world-cluster
        count: 1
        family: hello-world
        env_file: config.env
        ...

Terraform variable replacment
-----------------------------

If you're managing your AWS resources for your service with Terraform and you
export your Terraform state files to S3, or if you are using Terraform
Enterprise, you can use the values of your terraform outputs as string values
in your service definitions.

To do so, first declare a ``terraform`` top level section in your
``deployfish.yml`` file::

    terraform:
      statefile: 's3://terraform-remote-state/my-service-terraform-state'
      lookups:
        ecs_service_role: 'ecs-service-role'
        cluster_name: '{service-name}-ecs-cluster-name'
        elb_name: '{service-name}-elb-name'
        storage_bucket: 's3-{environment}-bucket'
        task_role_arn: '{service-name}-task-role-arn'
        ecr_repo_url: 'ecr-repository-url'

If using Terraform Enterprise you need to provide the ``workspace`` and ``organization``
in place of the statefile::

    terraform:
      workspace: sample_workspace
      organization: sampleOrganization
      lookups:
        ecs_service_role: 'ecs-service-role'
        cluster_name: '{service-name}-ecs-cluster-name'
        elb_name: '{service-name}-elb-name'
        storage_bucket: 's3-{environment}-bucket'
        task_role_arn: '{service-name}-task-role-arn'
        ecr_repo_url: 'ecr-repository-url'

Then, wherever you have a string value in your service definition, you can
replace that with a terraform lookup, like so::

    services:
      - name: my-service
        cluster: ${terraform.cluster_name}
        environment: prod
        count: 2
        load_balancer:
          service_role_arn: ${terraform.ecs_service_role}
          load_balancer_name: ${terraform.elb_name}
          container_name: my-service
          container_port: 80
        family: my-service
        network_mode: bridge
        task_role_arn: ${terraform.task-role-arn}
        containers:
          - name: my-service
            image: ${terraform.ecr_repo_url}:0.1.0
            cpu: 128
            memory: 256
            ports:
              - "80"
            environment:
              - S3_BUCKET=${terraform.storage_bucket}

statefile
^^^^^^^^^

(String, Required) The ``s3://`` URL to your state file.  For example,
``s3//my-statefile-bucket/my-statefile``.

lookups
^^^^^^^

(Required) A dictionary of key value pairs where the keys will be used
when doing string replacements in your service definition, and the values
should evaluate to a valid terraform output in your terraform state file.

You can use these replacements in the values:

  * ``{environment}``: replace with the value of the ``environment`` option for the current service
  * ``{service-name}``: replace with the name of the current service
  * ``{cluster-name}``: replace with the name of the cluster for the current service

These values are evaluated in the context of each service separately.

profile
^^^^^^^
(String, Optional) The name of the AWS CLI Named Profile to use when retrieving
the statefile from S3.

See `Named Profiles <https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html>`_

region
^^^^^^^
(String, Optional) The AWS region in which your S3 bucket lives.

workspace
^^^^^^^^^

(String, Required Terraform Enterprise) The Terraform Enterprise workspace.

organization
^^^^^^^^^^^^

(String, Required Terraform Enterprise) The Terraform Enterprise organization.


--tfe_token option
^^^^^^^^^^^^^^^^^^

In order to authenticate against terraform enterprise and read the state,
you need to provide an API token. This can be either a user API token,
team API token, or organization token.

    ``deploy --tfe_token <token> <subcommand> [options]``

It will also work if you specify an ``ATLAS_TOKEN`` environment variable
while using the ``--import_env`` option.

    ``deploy --import_env <subcommand> [options]``

Advanced Usage: using a different AWS Profile for the statefile
===============================================================

It is not uncommon to of your Terraform state files in a single bucket, even if
the associated Terraform templates affect resources in many different accounts.

If this is the case with you, you can specify which AWS Credentials named profile
(see `Named Profiles <https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html>`_
for more information).  use to retrieve the state files by adding the ``profile`` and ``region``
settings to your ``terrraform:`` section::

    terraform:
      statefile: 's3://hello-world-remotestate-file/hello-world-terraform-state'
      profile: configs
      region: us-west-2
      lookups:
        cluster_name: '{environment}-cluster-name'
        load_balancer_name: '{environment}-elb-id'
        task_role_arn: 'iam-role-hello-world-{environment}-task'
        rds_address: '{environment}-rds-address'
        app_bucket: 's3-hello-world-{environment}-bucket'

This will tell ``deployfish`` that, for retrieving this statefile only, it
should use the "configs" AWS profile.
