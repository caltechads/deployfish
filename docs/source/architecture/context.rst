=================================
Rebuild Domain Context (Glossary)
=================================

Command-line tool that deploys and operates containerized workloads on AWS
ECS from a declarative manifest. This glossary fixes the vocabulary used
across the other documents in this directory so rebuild specs stay
codebase-agnostic and internally consistent. When a spec uses a capitalized
term below, it means exactly the definition given here — not the old
implementation's class or field name.

Language
========

Manifest
--------
The declarative file a user writes describing clusters, services, and tasks
to deploy.

*Avoid:* deployfish.yml, config file, YAML file

Manifest Interpolation
----------------------
Substitution of external values (environment variables, infrastructure-as-code
outputs) into manifest fields before it is parsed.

*Avoid:* terraform lookup, env substitution

Cluster
-------
A named pool of compute capacity that hosts running workloads. Standard AWS
ECS concept; kept as-is because it's domain-standard, not tool-invented.

Cluster Node
------------
A single compute host (EC2 instance) that backs a Cluster's capacity.

*Avoid:* ContainerInstance, container instance

Service
-------
A long-running, self-healing workload definition: a desired count of copies
of a Workload Definition kept alive by the platform.

*Avoid:* ECS service (when discussing tool behavior, not the AWS API)

Workload Definition
--------------------
The versioned, immutable spec for how to run a workload: images, resources,
environment, secrets. A Service or Task points at one.

*Avoid:* TaskDefinition, task definition

Container Spec
---------------
One container's settings inside a Workload Definition (image, command,
ports, secrets, env).

*Avoid:* ContainerDefinition

One-Off Task
------------
A task the user runs on demand or on a schedule, independent of any
Service — not kept alive, not self-healing.

*Avoid:* StandaloneTask

Companion Task
--------------
A task defined alongside a Service and sharing its Workload Definition,
used for operational actions tied to that service (e.g. migrations,
one-time setup).

*Avoid:* ServiceHelperTask, helper task

Task Run
--------
A live execution instance produced by invoking a One-Off Task or Companion
Task — has its own lifecycle and exit status, separate from the definition
that produced it.

*Avoid:* InvokedTask

Secret Binding
--------------
A declared link from a Container Spec's environment to a value stored in an
external secret store (Parameter Store or Secrets Manager), resolved at
task launch.

*Avoid:* SecretsMixin, secrets block

Secret Namespace
-----------------
The prefix rule applied to a Secret Binding's backing key in the external
secret store, used to avoid collisions between unrelated Services/Tasks
that both bind a secret with the same short name.

*Avoid:* parameter prefix, path prefix

Deployment Rollout
-------------------
The end-to-end act of pushing a new or changed Workload Definition to a
running Service and waiting for it to stabilize.

*Avoid:* deploy, push

Intermediate Host
-------------------
The reachable host (a Cluster Node or a dedicated bastion instance) that an
operator connects through to reach a private resource that has no direct
network path from the operator's machine.

*Avoid:* jump host, bastion (as a standalone noun — use "Intermediate Host")

Bastion Tunnel
--------------
A temporary SSH-forwarded network path from the operator's machine, through
an Intermediate Host, to a private resource (e.g. a database) for
interactive access.

*Avoid:* SSHTunnel, tunnel (when ambiguous)

Remote Exec
-----------
Running an interactive or one-shot command inside a live container of a
running Service or Task, without an SSH tunnel.

*Avoid:* docker exec (when referring to the tool feature, not the
underlying mechanism)

Log Source
----------
The resolved log group and stream-prefix pair the tool tails or searches
for a given Service, One-Off Task, or Companion Task, derived automatically
from that workload's identity rather than supplied by the operator.

*Avoid:* log group, log stream (when referring to the tool's resolved
target, not the raw AWS resource)

Companion Task Command
-----------------------
The name used to select which of a Service's Companion Tasks an operation
(such as tailing logs or running the task) applies to.

*Avoid:* command name, helper name

Extension
---------
An optional, self-contained unit of added behavior (e.g. notifications,
database bootstrapping) loaded into the tool without changing its core.

*Avoid:* plugin (only when distinguishing from the core; "plugin" is fine
informally)

Extension Hook Point
----------------------
A named lifecycle moment (e.g. before or after a Deployment Rollout, on
Task Run completion) that an Extension can observe, without being able to
veto or alter the underlying operation.

*Avoid:* hook, callback

Resource Reference
-------------------
A manifest field that names another AWS resource the tool must look up and
bind at deploy time (e.g. an existing load balancer, subnet, or security
group), rather than one the tool creates.

*Avoid:* lookup, external resource

Scaling Policy
--------------
An autoscaling configuration the tool creates and manages on behalf of a
Service, distinct from a Resource Reference because the tool owns its
lifecycle rather than only reading it.

*Avoid:* autoscaling config, scaling target

Discovery Registration
------------------------
A service-discovery entry the tool creates and manages on behalf of a
Service, distinct from a Resource Reference because the tool owns its
lifecycle rather than only reading it.

*Avoid:* service discovery record, DNS registration
