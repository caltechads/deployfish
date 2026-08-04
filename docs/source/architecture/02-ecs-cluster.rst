===========
ECS Cluster
===========

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

A Cluster is the compute pool a Manifest's Services and Tasks run on. The
tool never creates a Cluster from scratch — a Cluster is a Resource
Reference the Manifest names, expected to already exist (created by
Terraform/CloudFormation/CDK or the AWS console). What the tool provides is
day-2 visibility and control over that pool: listing what's registered on
it, seeing what's running, and — for EC2-backed clusters — scaling the
Cluster Node count. Operators use this to answer "is there room to deploy"
and "what's actually running here right now" without leaving the CLI.

Concepts
========

- **Cluster** — a named pool of compute capacity (Fargate or EC2-backed)
  referenced by name in the Manifest.
- **Cluster Node** — an EC2 instance registered as a container instance in
  an EC2-backed Cluster; absent entirely for Fargate-backed Clusters.

Behavior
========

Identification and reference
-----------------------------

- The Manifest SHALL identify a Cluster by its AWS cluster name, not by ARN.
- Where a Cluster's Manifest entry names an Auto Scaling Group backing its
  Cluster Nodes, the tool SHALL resolve that group either from an explicit
  tag on the Cluster (a fixed, documented tag key) or by falling back to a
  group with the same name as the Cluster.
- When no Auto Scaling Group can be resolved for an EC2-backed Cluster, the
  tool SHALL treat that Cluster as unscalable rather than raising a fatal
  error on inspection.

Cluster type
------------

- The tool SHALL classify a Cluster as Fargate-backed when its default
  capacity provider strategy uses a Fargate capacity provider, and as
  EC2-backed otherwise.
- While a Cluster is Fargate-backed, the tool SHALL reject scale requests
  against it, since Fargate capacity is not operator-managed.

Inspection
----------

- When a Cluster inspection command is run, the tool SHALL report at
  minimum: cluster name, cluster type (Fargate/EC2), registered Cluster
  Node count, active Service count, running task count, and pending task
  count.
- When a listing command is run, the tool SHALL support filtering by
  cluster name using shell-glob-style patterns.
- When a Cluster named in the Manifest does not exist in AWS, any command
  that requires it to exist SHALL fail with a non-zero exit code and a
  message naming the missing Cluster, rather than returning an empty or
  partial result.

Cluster Node listing
---------------------

- The tool SHALL be able to list the EC2 instances currently registered as
  Cluster Nodes for a given Cluster, including instance ID and availability
  zone.
- The tool SHALL be able to list the tasks currently running on a Cluster,
  including which Cluster Node (if any) hosts each one, its Workload
  Definition family/revision, and its launch type.

Scaling
-------

- When a scale command is issued against an EC2-backed Cluster with a
  resolvable Auto Scaling Group, the tool SHALL set that group's desired
  capacity to the requested count.
- When the requested count falls outside the Auto Scaling Group's
  configured MinSize/MaxSize bounds and the caller has not requested a
  forced bounds change, the tool SHALL reject the request with a message
  stating the current bound and both remediation options (pick a count
  inside the bound, or force-adjust the bound).
- When the caller requests a forced bounds change and the count is outside
  bounds, the tool SHALL adjust the Auto Scaling Group's MinSize or MaxSize
  to accommodate the requested count before setting desired capacity.
- When a scale command is issued against a Cluster with no resolvable Auto
  Scaling Group, the tool SHALL fail with a non-zero exit code rather than
  silently doing nothing.

Command Surface
================

.. list-table::
   :header-rows: 1
   :widths: 20 30 35 15

   * - Command
     - Arguments / Flags
     - Effect
     - Exit codes
   * - ``cluster list``
     - ``--cluster-name <glob>`` (optional)
     - List Clusters visible in AWS, optionally filtered by a glob pattern
       on cluster name.
     - 0 on success
   * - ``cluster info <name>``
     - ``<name>`` (required, positional)
     - Show cluster name, type, Cluster Node count, active Service count,
       running/pending task counts for one Cluster.
     - 0 on success; non-zero if the Cluster does not exist
   * - ``cluster exists <name>``
     - ``<name>`` (required, positional)
     - Report whether the named Cluster exists in AWS.
     - 0 if it exists, non-zero otherwise
   * - ``cluster scale <name> <count>``
     - ``<name>``, ``<count>`` (required, positional); ``--force``
       (optional)
     - Set the Cluster's Auto Scaling Group desired capacity to
       ``<count>``; with ``--force``, also widen MinSize/MaxSize if needed.
     - 0 on success; non-zero if unscalable, out of bounds without
       ``--force``, or the Cluster does not exist
   * - ``cluster running-tasks <name>``
     - ``<name>`` (required, positional)
     - List tasks currently running on the Cluster, with hosting Cluster
       Node, Workload Definition, and launch type.
     - 0 on success; non-zero if the Cluster does not exist
   * - ``cluster ssh <name>`` / ``cluster run <name> <cmd>``
     - see :doc:`06-remote-access`
     - Interactive shell or one-shot command on a Cluster Node.
     - see :doc:`06-remote-access`

Open Questions
===============

- Whether ``cluster create``/``cluster update``/``cluster delete`` should
  exist at all: the old implementation exposed generic create/update/delete
  verbs on every resource type by default, but a Cluster is described here
  as a pure Resource Reference the tool never provisions. Recommend
  dropping create/update/delete for Cluster in the rebuild and keeping only
  list/info/exists/scale/running-tasks — confirm before implementation.
- Whether the Auto Scaling Group tag-based fallback lookup (a fixed tag key
  naming the group) should be a first-class Manifest field instead of an
  implicit AWS tag convention, for clarity and portability.
