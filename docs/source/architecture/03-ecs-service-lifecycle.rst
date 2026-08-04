==========================================
ECS Service Lifecycle & Deployment Rollout
==========================================

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

A Service is the primary long-running unit the tool manages: a self-healing
count of copies of a Workload Definition. Most day-to-day tool usage is
either standing up a new Service, or rolling out a change to one (a new
image, an environment change, a resource change) and watching it become
healthy. This document specifies how a Manifest's service block becomes a
live AWS ECS Service and Workload Definition, what a Deployment Rollout
does step by step, and every command that operates on a Service.

Concepts
========

- **Service** — this document is the primary owner of this term.
- **Workload Definition** — owned here; this document specifies how it is
  built from a Manifest and how it versions across rollouts.
- **Container Spec** — owned here; assembly rules for turning one
  Manifest container entry into one AWS container definition.
- **Companion Task** — referenced here (a Service may declare Companion
  Tasks that are saved as part of that Service's rollout); full behavior
  specified in :doc:`04-standalone-tasks`.
- **Deployment Rollout** — this document is the primary owner of this term.
- **Secret Binding** — referenced here (a Container Spec may declare Secret
  Bindings); full behavior in :doc:`05-secrets-management`.

Behavior
========

Workload Definition assembly
-----------------------------

- The system shall build one Workload Definition per Service from that
  Service's manifest block, combining: a family name, a network mode
  (default ``bridge`` unless ``launch_type`` is ``FARGATE``, in which case
  ``awsvpc`` networking is implied), one or more Container Specs, optional
  volumes, an optional task role, and — when ``launch_type`` is
  ``FARGATE`` — a required execution role.
- Where ``launch_type`` is ``FARGATE``, the system shall reject the
  Manifest if no execution role is supplied.
- The system shall reject a Service manifest block that declares zero
  containers.
- The system shall reject a volume declaration that specifies more than
  one of a host path, a Docker volume config, or an EFS config for the
  same volume; exactly one is required.
- Where a container omits its own memory limit, the system shall require a
  memory limit at the task level (EC2 launch type) or reject the Manifest.
- The system shall compute the task-level CPU and memory reservations from
  the sum of container-level reservations when the task level does not
  specify its own, consistent with AWS ECS task-definition sizing rules.

Immutability and versioning
-----------------------------

- The system shall never update an existing Workload Definition revision in
  place. Every Deployment Rollout that changes the Workload Definition
  shall register a brand-new, immutable revision in AWS ECS.
- The system shall never delete a Workload Definition revision.
- Each registered revision shall carry a last-updated timestamp as
  metadata, so operators can distinguish revisions produced by different
  rollouts even when the rendered definition is otherwise identical.

Deployment Rollout sequence
-----------------------------

When the operator triggers a Deployment Rollout for a Service (first
creation or update to an existing Service), the system shall, in order:

1. Save every Companion Task declared for the Service (registering their
   own Workload Definition revisions), and record each one's resulting
   family:revision as metadata on the Service's own Workload Definition,
   so operators can see which Companion Task revision shipped with which
   Service revision.
2. Register a new Workload Definition revision for the Service itself and
   capture its ARN.
3. Create or update the AWS Cloud Map service-discovery registration for
   the Service, if the Manifest declares one; remove it if the Manifest no
   longer declares one but AWS currently has one.
4. Create the Service in its target Cluster (first-ever rollout) or update
   the existing Service to point at the new Workload Definition revision
   (subsequent rollouts).
5. Create, update, or remove Application Auto Scaling registration for the
   Service to match the Manifest.
6. Wait for the Service to reach a stable state (see below) before
   reporting success.

- On first-ever creation, the system shall reject the operation without
  registering anything if a Service with the same name already exists in
  the target Cluster in AWS.
- On update, the system shall reject the operation if no Service with that
  name exists yet in AWS (the operator must create first).
- The system shall not alter the Service's current desired count as a side
  effect of a Deployment Rollout; desired count changes only through an
  explicit scale action.
- The system shall apply default rolling-update settings (200% maximum
  percent, 50% minimum healthy percent) when the Manifest does not specify
  its own deployment configuration.
- The system shall apply an ECS deployment circuit breaker (with automatic
  rollback to the previous stable revision on failure to stabilize) only
  when the Manifest explicitly enables it; the default is disabled.

Stabilization
--------------

- The system shall consider a Deployment Rollout stable when the AWS ECS
  "services stable" condition is met for that Service: the running count
  equals the desired count for the primary deployment, and no other
  deployment is still in progress.
- While waiting for stabilization, the system shall periodically display
  the Service's current deployments (status, Workload Definition revision,
  desired/pending/running counts) and any new Service events emitted by
  AWS since the wait began.
- The system shall time out waiting for stabilization after a configurable
  duration (default 15 minutes) and report the timeout distinctly from a
  hard failure, noting that a timeout does not necessarily mean the
  rollout failed — only that stabilization could not be confirmed in time.

Scaling
=======

- The system shall allow setting a Service's desired count independently
  of any Deployment Rollout, without registering a new Workload Definition
  revision.
- The system shall wait for the Service to stabilize after a scale action,
  the same way it does after a rollout.
- Scaling a Service is independent of scaling the Cluster's own compute
  capacity; the system shall not implicitly scale Cluster Nodes when
  scaling a Service.

Restart
=======

- The system shall support restarting all currently running tasks of a
  Service without registering a new Workload Definition revision and
  without changing desired count, by stopping each running task and
  letting AWS ECS start replacements from the same revision.
- The system shall reject a restart request for a Service with zero
  currently running tasks, reporting that there is nothing to restart.
- By default, the system shall stop tasks one at a time, waiting for the
  Service to stabilize after each stop, so capacity is never fully drained
  at once.
- Where the operator requests a hard restart, the system shall stop all
  running tasks immediately without waiting between stops, then wait once
  for the Service to stabilize afterward.

Deletion
========

- The system shall, when deleting a Service, first remove any Application
  Auto Scaling registration, remove any service-discovery registration,
  and unschedule any Companion Tasks that run on a schedule tied to that
  Service.
- The system shall scale the Service to zero and wait for it to stabilize
  at zero before issuing the delete, rather than deleting a Service that
  still has running tasks.
- The system shall require interactive confirmation (the operator must
  type the Service's name back) before deleting, unless invoked
  non-interactively with an explicit confirmation flag.

Preview
=======

- The system shall support a read-only "plan" action that computes and
  displays the difference between the Service and Workload Definition as
  currently declared in the Manifest and as currently deployed in AWS,
  without making any changes, so an operator can review a rollout before
  running it.

Command Surface
================

.. list-table::
   :header-rows: 1
   :widths: 18 30 35 17

   * - Command
     - Arguments / Flags
     - Effect
     - Exit behavior
   * - ``service info <name>``
     - ``--includes {secrets,deployments}``, ``--excludes {events}``
     - Show current AWS state of a Service by Manifest name or AWS
       identifier.
     - 0 on success; non-zero if the Service does not exist.
   * - ``service list``
     - ``--cluster-name``, ``--service-name`` (glob patterns), ``--launch-type
       {any,EC2,FARGATE}``, ``--scheduling-strategy {any,REPLICA,DAEMON}``,
       ``--updated-since YYYY-MM-DD``
     - List matching Services across the account.
     - 0 always (empty list is not an error).
   * - ``service exists <name>``
     - —
     - Report whether the Service exists in AWS.
     - 0 always; result communicated in output.
   * - ``service plan <name>``
     - —
     - Show the diff between Manifest-declared and AWS-deployed state
       without applying it.
     - 0 on success.
   * - ``service create <name>``
     - —
     - Run the full Deployment Rollout sequence to stand up a new Service.
       Refuses if the Service already exists.
     - Non-zero if the Service already exists or stabilization fails.
   * - ``service update <name>``
     - —
     - Run the full Deployment Rollout sequence against an existing
       Service. Refuses if the Service does not exist.
     - Non-zero if the Service does not exist or stabilization fails.
   * - ``service delete <name>``
     - interactive confirmation prompt
     - Deregister auto scaling and service discovery, unschedule Companion
       Tasks, scale to zero, then delete the Service.
     - Non-zero if the confirmation does not match or deletion fails.
   * - ``service scale <name> <count>``
     - ``count`` (integer, positional)
     - Set desired count on the existing Service and wait for
       stabilization.
     - Non-zero if the Service does not exist or fails to stabilize.
   * - ``service restart <name>``
     - ``--hard``
     - Stop and replace all running tasks of the Service, in place, on
       the current Workload Definition revision.
     - Non-zero if there are no running tasks, or if stabilization fails.
   * - ``service running-tasks <name>``
     - —
     - List the tasks currently running for the Service, with their
       Cluster Node, availability zone, and Workload Definition revision.
     - 0 on success.

Open Questions
================

- Whether "hard" restart should also expose a configurable batch size
  (stop N at a time) rather than only all-at-once vs one-at-a-time — not
  present in current behavior, worth deciding fresh for the rebuild.
- Whether the Deployment Rollout timeout and polling interval should be a
  Manifest-level setting rather than only an environment variable —
  current behavior reads it from an environment variable only.
- Exact non-zero exit code values are not specified here (current
  behavior does not appear to differentiate error classes by exit code
  beyond zero/non-zero); the rebuild should decide whether distinct exit
  codes per failure class (not-found vs stabilization-timeout vs
  validation) are worth adding.
