## 1.0.0 (2021-05-17)

ENHANCEMENTS:

  * Complete refactoring of the deployfish codebase
    * Django like models and managers for all AWS resources
    * Jinja2 and python-tabulate for rich output
    * Class based views for click commands
    * Many other changes
  * FEATURE: You can now work with all Services and Tasks in your AWS account, even if they're not listed in your deployfish.yml file
  * FEATURE: Service helper tasks can now be scheduled
  * FEATURE: Service helper tasks logging now defaults to awslogs when configured for FARGATE
  * FEATURE: All standalone tasks (in the top level tasks: section) for a service can now be updated with a single command
  * FEATURE: You can now look at task logs in CloudWatch Logs with deployfish
  * FEATURE: Describe ALBs, Target Groups
  * FEATURE: Describe ELBs
  * UPDATE: Service info output now includes details about load balancing setup

## 0.30.1 (2019-12-17)

BUG FIXES:
  
  * cli: properly handle multiple target groups when describing a service

## 0.30.0 (2019-12-17)

ENHANCEMENTS:

  * service: you can now specify multiple target groups for a service
  * service: you can now specify Capacity Provider Strategies for a service
  * cli: now helpfully show all services and environments when you give a service/environment name that doesn't exist.

## 0.29.9 (2019-10-14)

BUG FIXES:

  * task: now actually setting security groups properly when using task scheduling

## 0.29.8 (2019-10-14)

ENHANCEMENTS:

  * service/***task-definition: now adding entries from the `config:` section of the task definition to
    container secrets.  Thus you no longer need to set `deploy entrypoint` as your container's `ENTRYPOINT`
    in order to get your `config:` entries out of SSM Parameter Store.  

## 0.29.7 (2019-04-18)

BUG FIXES:

  * task/task-definition: now actually setting security groups properly for the task

## 0.29.5 (2019-10-07)

ENHANCEMENTS:

  * config/terraform: you can now use `{environment}`, `{service-name}` and `{cluster-name}` keyword replacements in the
    terraform statefile url
  * global: now requiring PyYAML >= 5

## 0.29.1 (2019-07-14)

ENHANCEMENTS:

  * config/terraform: now correctly parsing terraform-0.12.x format state files

## 0.29.0 (2019-05-30)

ENHANCEMENTS:

  * cli: Added the `deploy parameters` subcommand, which allows you to manage `:external:` type parameters in AWS SSM
    Parameter Store.

## 0.28.1 (2019-04-18)

BUG FIXES:

  * We should no longer be creating invalid `cpu` Cloudwatch Alarms when Application Autoscaling is defined for the
    service []

## 0.28.0 (2019-04-16)

FEATURES:

  * **New resource**: `tasks:`, Standalone task support, outside of an ECS service

## 0.27.0 (2019-01-04)

ENHANCEMENTS:

  * service/task-definition: Added tmpfs support for ECS container definitions (ChrisLeeTW)
  * serivce: Added support for target tracking to our Application Autoscaling implementation (rv-vmalhotra)

## 0.26.0 (2018-11-30)

ENHANCEMENTS:

  * service, service/task-definition: Added full docker volumes support
  * service/task-definition: Added `cap_add` and `cap_drop` to our ECS container definitions
