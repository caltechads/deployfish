**************
Load Balancing
**************

Problem
=======

We often want to scale an application to run on more than one running container, either for performance or reliability reasons. In this tutorial, we'll add a load balancer to balance the load across two containers.

Setup
=====

To our basic setup in the previous tutorials, we need to add a load balancer. We're using an AWS Elastic Load Balancer (ELB) and naming it *hello-world-elb* in our example.

Configuration
=============

Here's the configuration file for this load balanced service::

    services:
      - name: hello-world-test
        cluster: hello-world-cluster
        count: 1
        family: hello-world
        load_balancer:
          service_role_arn: arn:aws:iam::123445564666:role/ecsServiceRole
          load_balancer_name: hello-world-elb
          container_name: hello-world
          container_port: 80
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

Here we've added the new parameter, *load_balancer*. This corresponds to the AWS ELB.

Load Balancer Parameters
------------------------

ELB
^^^

The *load_balancer* parameter requires the following four parameters if you are using and AWS ELB:

*service_role_arn*
    The name or full ARN of the IAM role that allows ECS to make calls to your load balancer on your behalf. You will need to used the ARN that corresponds to your account.

*load_balancer_name*
    The name of the ELB.

*container_name*
    The name of the container to associate with the load balancer

*container_port*
    The port on the container to associate with the load balancer. This port must correspond to a container port on container container_name in your service’s task definition

ALB
^^^

AWS also offers the Application Load Balancer (ALB). I'f you are using that instead of the ELB, you will still use the *load_balancer* parameter, but it will require *target_group_arn* to be specified, rather than *load_balancer_name*:

*target_group_arn*
    The full ARN of the target group to use for this service.

Deploy
======

To deploy this service, run the same command we ran in the last tutorial::

    deploy create hello-world-test

To increase the number of running containers behind the load balancer to 2 instances, you can either modify the config, setting the count to::

    services:
      - name: hello-world-test
        cluster: hello-world-cluster
        count: 2
        family: hello-world
        load_balancer:
        ...

Then running *update*::

    deploy update hello-world-test

Or you can scale the container arbitrarily with the *scale* command::

    deploy scale test 2

