========
Overview
========

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

This document set specifies a command-line tool for deploying and operating
containerized workloads on AWS ECS from a single declarative Manifest. The
tool exists so a small team can describe "what should be running" in one
file, check it into version control, and drive every lifecycle
action — first deploy, redeploy, scale, run a one-off job, inspect logs, get
a shell inside a running container, tunnel to a private database — through
one consistent command surface, without hand-rolling AWS CLI / boto3
invocations or Terraform for day-2 operations.

It is a rebuild: the specs in this directory describe *what the tool must
do and why*, independent of any previous implementation's frameworks,
class names, or module layout. AWS ECS is the fixed target platform;
nothing here abstracts ECS away behind a generic "scheduler" concept.

Primary users
=============

- **Service owner / developer**: writes the Manifest, runs deploys,
  inspects logs, execs into containers to debug.
- **Operator / on-call**: runs One-Off Tasks (migrations, backfills),
  opens Bastion Tunnels to databases, scales Services under load.
- **CI pipeline**: runs the same commands non-interactively to deploy on
  merge.

Outcomes
========

- A single Manifest is the source of truth for a Cluster's Services, their
  Workload Definitions, and any One-Off or Companion Tasks.
- A Deployment Rollout is a single command, is idempotent, and fails loud
  (non-zero exit, clear message) rather than leaving a Service half-updated
  without indication.
- Secrets never live in the Manifest in plaintext; they are declared as
  Secret Bindings resolved from an external store at task launch.
- Any workload's logs and running containers are reachable by name from the
  command line, without the operator hand-tracking ARNs or log group names.
- The command surface is scriptable: consistent flags, predictable exit
  codes, machine-parseable output on request.

Command surface, by area
=========================

The full command grammar and flags for each area are specified in that
area's own document, alongside the business rules it implements:

.. list-table::
   :header-rows: 1

   * - Area
     - Document
   * - Manifest format and interpolation
     - :doc:`01-configuration-model`
   * - Cluster inspection and node management
     - :doc:`02-ecs-cluster`
   * - Service lifecycle and Deployment Rollout
     - :doc:`03-ecs-service-lifecycle`
   * - One-Off Task and Companion Task execution
     - :doc:`04-standalone-tasks`
   * - Secret Binding declaration and resolution
     - :doc:`05-secrets-management`
   * - Bastion Tunnels and Remote Exec
     - :doc:`06-remote-access`
   * - Log discovery and tailing
     - :doc:`07-observability`
   * - RDS, load balancers, autoscaling, service discovery
     - :doc:`08-supporting-infra`
   * - Extension points
     - :doc:`09-extensibility`

Non-goals
=========

- Not a general infrastructure-provisioning tool (no VPC/subnet/IAM
  creation) — it consumes existing infrastructure via Resource References
  and expects Terraform/CloudFormation/CDK to have created it.
- Not a CI/CD pipeline system — it is the deploy step a pipeline calls,
  not the pipeline itself.
- Not multi-cloud — AWS ECS only.

Open Questions
===============

- None at this level; area-specific open questions are tracked in each
  document.
