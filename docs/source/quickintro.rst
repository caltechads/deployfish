``deployfish`` has commands for managing the whole lifecycle of your application:

* Create, update, destroy and restart ECS services
* Manage multiple environments for your service (test, qa, prod, etc.)
* View the configuration and status of running ECS services
* Scale the number of containers in your service, optionally scaling its
  associated autoscaling group at the same time
* Update a running service safely
* Run a one-off command related to your service
* Configure load balancing
* Configure application autoscaling
* Configure placement strategies
* Manage AWS Parameter Store and utilize in containers
* Add additional functionality through modules

Additionally, ``deployfish`` integrates with
`terraform <https://www.terraform.io>`_ state files so that you can use the
values of terraform outputs directly in your ``deployfish`` configurations.
