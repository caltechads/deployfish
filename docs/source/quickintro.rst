``deployfish`` has commands for managing the whole lifecycle of your application:

* Safely and easily create, update, destroy and restart ECS services
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

Additionally, ``deployfish`` integrates with
`Terraform <https://www.terraform.io>`_ state files so that you can use the
values of terraform outputs directly in your ``deployfish`` configurations.
