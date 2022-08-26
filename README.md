```
      _            _              __ _     _
     | |          | |            / _(_)   | |
   __| | ___ _ __ | | ___  _   _| |_ _ ___| |__
  / _` |/ _ \ '_ \| |/ _ \| | | |  _| / __| '_ \
 | (_| |  __/ |_) | | (_) | |_| | | | \__ \ | | |
  \__,_|\___| .__/|_|\___/ \__, |_| |_|___/_| |_|
            | |             __/ |
            |_|            |___/
```

`deployfish` has commands for managing the whole lifecycle of your application:

* Safely and easily create, update, destroy and restart ECS services
* Safely and easily create, update, run, schedule and unschedule ECS tasks
* Extensive support for ECS related services like load balancing, application
  autoscaling and service discovery
* Easily scale the number of containers in your service, optionally scaling its
  associated autoscaling group at the same time
* Manage multiple environments for your service (test, qa, prod, etc.) in
  multiple AWS accounts.
* Uses AWS Parameter Store for secrets for your containers
* View the configuration and status of running ECS services
* Run a one-off command related to your service
* Easily exec through your VPC bastion host into your running containers, or
  ssh into a ECS container machine in your cluster.
* Setup SSH tunnels to the private AWS resources in VPC that your service
  uses so that you can connect to them from your work machine.

* Extensible! Add additional functionality through custom deployfish modules.
* Works great in CodeBuild steps in a CodePipeline based CI/CD system!


Additionally, `deployfish` integrates with
[terraform](https://www.terraform.io) state files so that you can use the
values of terraform outputs directly in your `deployfish` configurations.

To use `deployfish`, you

* Install `deployfish`
* Define your service in `deployfish.yml`
* Use `deploy` to start managing your service

A simple `deployfish.yml` looks like this:

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
            memoryReservation: 128
            ports:
              - "80"
            environment:
              - ENVIRONMENT=prod
              - ANOTHER_ENV_VAR=value
              - THIRD_ENV_VAR=value

See the `examples/` folder in this repository for example `deployfish.yml`
files.

## Documentation

[deployfish.readthedocs.io](http://deployfish.readthedocs.io/) is the full
reference for deployfish, including a full `deployfish.yml` reference and
tutorials.


## Installing deployfish

deployfish is a pure python package.  As such, it can be installed in the
usual python ways.  For the following instructions, either install it into your
global python install, or use a python [virtual environment](https://python-guide-pt-br.readthedocs.io/en/latest/dev/virtualenvs/) to install it
without polluting your global python environment.

### Install deployfish

    pip install deployfish

### Install AWS CLI v2

deployfish requries AWS CLI v2 for some of its functionality, notably EXEC'ing into FARGATE containers.  While AWS CLI
v1 was installable via `pip`, AWS CLI v2 is not, so we have to do the install manually.  Here's how to set that up on a
Mac:

    # Uninstall any old versions of the cli
    pip uninstall awscli

    # Deactivate any pyenv environment so we can be in the system-wide Python interpreter
    cd ~

    # Install the new AWS CLI from brew -- it's no longer pip installable
    brew update
    brew install awscli

    # Install the Session Manager plugin
    curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"
    unzip sessionmanager-bundle.zip
    sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin


If later on you have issues with EXEC'ing or with the `aws` command in general, check to ensure you're getting your
global version of `aws` instead of an old one in your current virtual environment:

    aws --version

If the version string shows version < 2:

    pip uninstall awscli
