=========================
Supporting Infrastructure
=========================

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

A Service does not run alone: it sits behind a load balancer, scales with
demand, registers itself for discovery, sometimes mounts shared storage,
and sometimes needs to read connection details for a database it doesn't
own. These resources are grouped separately from
:doc:`03-ecs-service-lifecycle` because they share one property that the
core Service/Task lifecycle does not: **the tool never creates or destroys
them**. They are provisioned by other means (Terraform, the console, a DBA)
and the tool only *references*, *inspects*, or *attaches to* them. Getting
this created-vs-referenced boundary right is the main point of this
document.

Concepts
========

RDS
---

- **Resource Reference**: an RDS instance identifier or ARN, resolved for
  read-only inspection and credential lookup. Never created by the tool.

Load Balancing
--------------

- **Resource Reference**: a load balancer name/ARN or target group ARN,
  attached to a Service's manifest entry. Never created by the tool.

Autoscaling
-----------

- **Resource Reference**: an EC2 Auto Scaling Group name, attached to a
  Service for coupled scaling. Never created by the tool.
- Application Auto Scaling (CPU-based Service task-count scaling) *is*
  declared and created by the tool as part of a Service — this is the one
  exception to "supporting infra is reference-only" in this document, since
  it's inseparable from the Service's own scaling behavior.

Service Discovery
------------------

- A Service Discovery entry (Route 53 private DNS record) *is* created by
  the tool as part of Service creation, bound permanently to that Service.

File Storage
-------------

- **Resource Reference**: an EFS file system ID, mounted as a volume into a
  Workload Definition's containers. Never created by the tool.

Behavior
========

RDS
---

- The system shall resolve an RDS instance by identifier or ARN and report
  its engine, version, endpoint hostname/port, Multi-AZ status, VPC,
  subnets, and security groups.
- Where the RDS instance's root credentials are stored in Secrets Manager,
  the system shall retrieve and display the root username and password on
  request.
- Where the RDS instance's root credentials are not stored in Secrets
  Manager, the system shall display the root username only and state
  plainly that the password is not available via Secrets Manager.
- The system shall never create, modify, or delete an RDS instance.

Load Balancing
--------------

- Where a Service declares a classic load balancer, the manifest shall
  specify the load balancer's name, the container name, and the container
  port to register; the referenced container and port shall exist in the
  Service's Workload Definition.
- Where a Service declares an ALB/NLB attachment, the manifest shall
  specify one or more target group ARNs, each with a container name and
  container port.
- The system shall reject a Service manifest that declares both a classic
  load-balancer attachment and a target-group attachment.
- Once a Service is created, the system shall treat its load balancer /
  target group attachment as immutable: changing it requires destroying
  and recreating the Service, and the system shall say so rather than
  attempting an in-place update.
- Where a Workload Definition's network mode is set for per-task
  networking (e.g. one elastic network interface per task), the system
  shall require the referenced target group to be configured for IP-based
  targets, and should warn if it detects an instance-targeted target group
  in that configuration.
- The system shall list load balancers filterable by VPC ID, name (glob
  pattern), type (application/network/any), and scheme
  (internet-facing/internal/any), and shall never create or delete one.

Autoscaling
-----------

- Where a Service declares an Auto Scaling Group name, a scale command
  issued against that Service shall also adjust the named group's
  desired/min/max capacity in step with the Service's task count.
- Where a Service instead declares a capacity provider strategy, the
  system shall pass that strategy to the Service definition and shall not
  attempt to directly manipulate any Auto Scaling Group's capacity, since
  scaling is delegated to the capacity provider.
- A Service manifest shall not declare both an Auto Scaling Group name and
  a capacity provider strategy.
- Where a Service declares Application Auto Scaling, the manifest shall
  specify a minimum capacity, a maximum capacity, an IAM role ARN
  authorizing scaling actions, and exactly two named rules: `scale-up` and
  `scale-down`.
- Each scaling rule shall specify a CPU threshold comparison, an evaluation
  window (check interval x number of periods), a cooldown period, and the
  task-count delta to apply when triggered.
- The system shall create/update the Application Auto Scaling policy as
  part of Service create/update, and shall remove it if the manifest no
  longer declares it.

Service Discovery
------------------

- Where a Service declares service discovery, the manifest shall specify a
  private DNS namespace, a discovery service name, and at least one DNS
  record (type A or SRV, with a TTL).
- The system shall create the Service Discovery entry when the Service is
  created, and shall treat it as immutable thereafter: the system shall
  refuse to change a Service's discovery configuration in place, requiring
  destroy-and-recreate instead.

File Storage
-------------

- A manifest may declare named volumes at the Service or Task level.
  Each volume shall be one of: a Docker-volume-driver-backed volume
  (task-scoped or shared-scoped, with driver name, optional driver options,
  and optional labels), an EFS-backed volume (file system ID and optional
  root directory, defaulting to `/`), or a host-bind-mount volume (host
  path).
- An EFS-backed or Docker-volume-driver-backed volume shall be usable by
  either EC2 or Fargate launch type; a Docker-volume-driver-backed volume
  shall only be usable with the EC2 launch type, since Fargate does not
  support third-party volume drivers.
- A Container Spec that mounts a named volume shall reference a volume
  name declared at the Service or Task level; the system shall reject a
  mount referencing an undeclared volume name.
- The system shall never create, modify, or delete an EFS file system; it
  only references one by ID.

Command Surface
================

RDS
---

.. list-table::
   :header-rows: 1

   * - Command
     - Arguments / Flags
     - Effect
     - Exit Codes
   * - ``rds list``
     - none
     - List all RDS instances visible in the account/region, ordered by
       name; shows name, VPC, engine, version, Multi-AZ, hostname, root
       user.
     - 0 success
   * - ``rds info <pk>``
     - ``pk``: instance identifier or ARN
     - Show full detail for one RDS instance.
     - 0 success; 1 not found
   * - ``rds credentials <pk>``
     - ``pk``: instance identifier or ARN
     - Print root username, and root password if Secrets-Manager-enabled
       (otherwise a notice that the password isn't available).
     - 0 success; 1 not found

Load Balancing
--------------

.. list-table::
   :header-rows: 1

   * - Command
     - Arguments / Flags
     - Effect
     - Exit Codes
   * - ``lbs list``
     - ``--vpc-id``, ``--name`` (glob), ``--type``
       (any/application/network), ``--scheme``
       (any/internet-facing/internal)
     - List ALBs/NLBs matching filters.
     - 0 success
   * - ``lbs info <pk>``
     - ``pk``: name or ARN
     - Show full detail for one ALB/NLB, including attached target groups.
     - 0 success; 1 not found

Autoscaling
-----------

No standalone command group; behavior is exposed through
:doc:`03-ecs-service-lifecycle`'s ``service scale`` command, which also
adjusts an attached Auto Scaling Group's capacity when one is declared.

Service Discovery
------------------

No standalone command group; configured declaratively in the manifest and
applied during ``service create`` / ``service update`` (see
:doc:`03-ecs-service-lifecycle`).

File Storage
-------------

No standalone command group; volumes are declared in the manifest and take
effect at Workload Definition registration time (see
:doc:`03-ecs-service-lifecycle` and :doc:`04-standalone-tasks`).

Open Questions
===============

- Should "Application Auto Scaling" and "Service Discovery" (tool-created,
  Service-bound) get their own glossary terms distinct from
  "Resource Reference" (tool-referenced, externally-created)? Recommend
  adding **Scaling Policy** and **Discovery Registration** to
  ``context.rst`` to make this distinction explicit rather than leaving it
  implicit in prose — flagging rather than inventing unilaterally.
