***************
A Basic Service
***************


Problem
=======

In this tutorial we will configure the bare essentials. Everything in the configuration is required. Further tutorials will look at some of the optional parameters.

The configuration below will result in a single container running in an AWS ECS cluster. The container is built from a simple nginx based hello-world image available on http://dockerhub.com, named `tutum/hello-world <https://hub.docker.com/r/tutum/hello-world/>`_.

Setup
=====

In order to deploy this configuration, you will need an AWS ECS cluster, containing at least one EC2 machine, on which to run the container. You can either create a cluster named *hello-world-cluster* or change the *cluster* parameter in the configuration file to correspond to the name of the cluster that you created.

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

AWS ECS is made up of *services*, *tasks*, and *task definitions*. The *task definitions* define the *task* or *service*. A *task* is a container that runs and exits, while a *service* is a container that stays running, like a web server, and will be restarted by ECS if it shuts down unexpectedly.

The configuration files you will use with *deployfish* are `YAML <https://en.wikipedia.org/wiki/YAML>`_ based. A typical project or application will have a single *deployfish.yml* file, containing all of the project's relevant services. This initial example only defines a single service.

If you want to define additional services, you simply have to add another name to the *services* array, along with its corresponding parameters::

    services:
        - name: name1
          cluster: cluster1
          ...
        - name: name2
          cluster: cluster2
          ...

Required Service Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each *service* contains at least the five following required parameters:

*name*
    The name of the ECS service. In this case, it is *hello-world-test*. This has to be unique.

*cluster*
    The ECS cluster that will run the resultant container.

*count*
    The number of containers to run, which is 1 in this case.

*family*
    The base name of the *task definition*. Each revision of your image will have its own *task definition* consisting of the base name and the revision number. We are naming this base name *hello-world*.

*container*
    This parameter defines the containers to be run.

Required Container Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each *container* in the *service* contains at least the four following required parameters:

*name*
    The name of the container.

*image*
    The Docker image to use. If your image is in AWS ECR, you will use the full format::

        <account number>.dkr.ecr.<region>.amazonaws.com/<image>:<version>

    Since we're pulling an image from Dockerhub, we just need to supply the image name::

        tutum/hello-world

*cpu*
    The number of cpu units to reserve for the container.

*memory*
    The hard limit of memory (in MB) available to the container.



Deploy
======

To deploy this service, add your configuration to the *deployfish.yml* file and in the same directory as your configuration file run::

    deploy create hello-world-test

If you have named your configuration file something else, you can run::

    deploy -f myconfigfile.yml create hello-world-test

Assuming everything ran successfully, you should be able to see the relevant info with::

    deploy info hello-world-test

If you make a change and would like to update the service run::

    deploy update hello-world-test

