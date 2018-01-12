*****************
Fargate Tutorial
*****************


Problem
=======

In :doc:`tutorial2`, we looked at an nginx based hello-world web site running on ECS EC2. In this tutorial we will see how to create the same service running on 
ECS Fargate.

Setup
=====

We just need the same basic setup that we had in the first tutorial, namely an ECS cluster named *hello-world-cluster*, but we will not need any EC2 instances.

Configuration
=============

Here's the configuration file for this service::

    services:
      - name: hello-world-test
        cluster: hello-world-cluster
        count: 1
        family: hello-world
        network_mode: awsvpc
        launch_type: FARGATE
        execution_role: arn:aws:iam::123142123547:role/my-task-role
        cpu: 256
        memory: 512
        vpc_configuration:
          subnets:
            - subnet-12345678
            - subnet-87654321
          security_groups:
            - sg-12345678
          public_ip: ENABLED
        containers:
          - name: hello-world
            image: tutum/hello-world
            cpu: 128
            memory: 256
            ports:
              - "80"
            command: /usr/bin/supervisord
            environment:
              - VAR1=test
              - VAR2=anothervar
              - DEBUG=True

You will notice that we have added several new parameters - *launch_type*, *execution_role*, *cpu*, *memory*,
and *vpc_configuration*:

*launch_type*
    This is the parameter that specifies whether the service is an EC2 service or a FARGATE service. The default value is EC2
    so you only need to specify this for a Fargate task.

*execution_role*
    This is the task exeuction role ARN for an IAM role that allows Fargate to pull container images and publish container logs
    to Amazon CloudWatch on your behalf

*cpu*
    For Fargate tasks you are required to define the cpu at the task level, and there are specific values that are allowed.

==================
CPU value
==================
 256 (.25 vCPU)
 512 (.5 vCPU)
 1024 (1 vCPU)
 2048 (2 vCPU)
 4096 (4 vCPU)

*memory*
    For Fargate tasks you are required to define the memory at the task level, and there are specific values that are allowed.

=====================================================================================
 Memory value (MiB)
=====================================================================================
 512 (0.5GB), 1024 (1GB), 2048 (2GB)
 1024 (1GB), 2048 (2GB), 3072 (3GB), 4096 (4GB)
 2048 (2GB), 3072 (3GB), 4096 (4GB), 5120 (5GB), 6144 (6GB), 7168 (7GB), 8192 (8GB)
 Between 4096 (4GB) and 16384 (16GB) in increments of 1024 (1GB)
 Between 8192 (8GB) and 30720 (30GB) in increments of 1024 (1GB)

*vpc_configuration*
    The vpc configuration for any Fargate tasks requires the following four parameters:

    *subnets (array)*
        The subnets in the VPC that the task scheduler should consider for placement. 
        Only private subnets are supported at this time. The VPC will be determined by the subnets you
        specify, so if you specify multiple subnets they must be in the same VPC.
    *security_groups (array)*
        The ID of the security group to associate with the service.
    *public_ip (string)*
        Whether to enabled or disable public IPs. Valid Values are ``ENABLED`` or ``DISABLED``



Deploy
======

To deploy this service, run the same command we ran in the last tutorial::

    deploy create hello-world-test

