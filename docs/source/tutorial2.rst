*****************
More Funtionality
*****************


Problem
=======

In :doc:`tutorial1`, we looked at the essentials of a service. We hosted an nginx based hello-world web site. A fundamental flaw with this site, though, is that it isn't accessible from anywhere but the local Docker container, which isn't terribly useful. We need to open the relevant ports to make it available. We're also going to set some environment variables and overwrite the Docker *command*.

Setup
=====

We just need the same basic setup that we had in the first tutorial, namely an ECS cluster of at least one EC2 machine named *hello-world-cluster*

Configuration
=============

Here's the configuration file for this service::

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
            ports:
              - "80"
            command: /usr/bin/supervisord
            environment:
              - VAR1=test
              - VAR2=anothervar
              - DEBUG=True

Here we've added three new parameters - *ports*, *command*, and *environment*:

*ports*
    This is a list of values, so each value begins with a dash. In our case, we are just opening up one port, so we just have the single value, *80*. This will open port 80, hosting it on a random port on the ECS cluster machine that is hosting the container.

*command*
    This is the Docker *command* that will be run when the container is started

*environment*
    This is a list of values, so each begins with a dash. It is always in the form::

        - VARIABLE=VALUE

    Anything set here will be available in the environment of the running container.

Port Options
^^^^^^^^^^^^

If you want to specify the port number on the ECS cluster machine that will correspond to the container's port, you can specify that in the form HOST_PORT:CONTAINER_PORT::

    ports:
      - "8000:80"

The *hello-world* web site will then be avialable on port 8000 of the ECS cluster machine that is hosting the container.

Deploy
======

To deploy this service, run the same command we ran in the last tutorial::

    deploy create hello-world-test

