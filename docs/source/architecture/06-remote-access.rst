==============
Remote Access
==============

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

Once a Workload Definition is running, developers and operators still need
to get inside it: to open an interactive shell for debugging, to run a
one-off diagnostic command across every Cluster Node backing a Service, or
to reach a private resource — most often a database — that has no public
endpoint. This document specifies two related but distinct capabilities:

- **Remote Exec** — running a command inside a live container of a running
  Service or Task Run, for interactive debugging or quick inspection.
- **Bastion Tunnel** — forwarding a local port through an intermediate host
  in the target VPC to a private host:port, so a local client (a database
  GUI, `psql`, etc.) can reach a resource that has no route from the
  operator's machine.

Both are interactive, foreground operations aimed at a human at a keyboard,
not automation — CI pipelines use :doc:`03-ecs-service-lifecycle` and
:doc:`04-standalone-tasks` instead.

Concepts
========

- **Bastion Tunnel** (glossary) — this document is its primary owner: how
  it is declared, targeted, and established.
- **Remote Exec** (glossary) — this document is its primary owner.
- **Cluster Node** (glossary) — the compute host a Bastion Tunnel or
  SSH-based Remote Exec passes through.
- **Intermediate Host** (new sub-term of Bastion Tunnel) — the specific
  Cluster Node, jump box, or SSM-managed instance chosen to carry a given
  tunnel or exec session. Flagged in Open Questions for possible glossary
  promotion.

Behavior
========

Remote Exec
-----------

- The system shall support two distinct Remote Exec transports depending on
  how a Workload Definition's Container Spec is configured:

  1. **In-container exec**, used when the Container Spec has command
     execution enabled at the platform level (an ECS "execute command"
     capability) — works for both EC2- and Fargate-backed workloads,
     requires no SSH access to the underlying host.
  2. **SSH-based exec**, used when in-container exec is not enabled and the
     workload is backed by EC2 Cluster Nodes — the tool SSHes to the
     Cluster Node hosting the target container and runs `docker exec`
     there. This transport is unavailable for Fargate-backed workloads,
     which have no reachable host.

- When the user targets a Service or Task Run for Remote Exec, and
  in-container exec is enabled, the system shall use in-container exec
  regardless of launch type.
- When in-container exec is not enabled and the workload is Fargate-backed,
  the system shall reject the request with a clear error stating Remote
  Exec is unavailable for this workload, rather than silently failing.
- When more than one container across more than one running Task Run could
  satisfy the request, the system shall by default choose one
  automatically (deterministically, e.g. first running Task Run's first
  container).
- Where the user passes a "choose interactively" flag, the system shall
  list every running Task Run + container combination (with enough
  identifying detail — host/task id, container name, container version —
  to distinguish them) and prompt for a numbered selection.
- When no running Task Run exists for the target, the system shall fail
  with an explicit "no running tasks" error rather than hanging or
  connecting to nothing.
- The system shall also support running a single shell command
  (non-interactively) against one or all Cluster Nodes associated with a
  Service or Task's running tasks, capturing and labeling each target's
  output (and distinguishing success from failure per target) so multi-node
  results are attributable.

Bastion Tunnel
--------------

- The system shall let a Manifest declare a named Bastion Tunnel scoped to
  a Service, specifying: a tunnel name, the target host (a hostname/IP, or
  a Resource Reference to a Secret Binding holding the value), the target
  port, and the local port to bind on the operator's machine.
- Where the declared host or port value points at a Secret Binding rather
  than a literal value, the system shall resolve it from the secret store
  at tunnel-establishment time, not at Manifest-parse time.
- The system shall support at least two intermediate-host strategies,
  selectable per Service:

  1. **Bastion host** — an intermediate host explicitly tagged/designated
     as the VPC's bastion, reachable via SSH, used purely as a network
     hop (not related to the target Service's own Cluster Nodes).
  2. **Direct-to-node** — a Cluster Node already running the target
     Service (or, for Fargate-backed services, a provisioned network
     endpoint in the same VPC) used as the intermediate host, via SSM
     session forwarding rather than a separate bastion.

- When "bastion host" strategy is selected but no bastion host can be found
  in the target VPC, the system shall fail with an explicit error rather
  than falling back silently to another strategy.
- When more than one candidate intermediate host exists, the system shall
  by default choose one automatically, and shall support a "choose
  interactively" flag that lists candidates (name, instance id, IP) for
  numbered selection.
- The system shall keep an established Bastion Tunnel open in the
  foreground until the user terminates it (e.g. Ctrl-C) or the underlying
  connection drops, and shall not leave orphaned port-forward processes
  running after termination.
- Before establishing a tunnel, the system shall print the resolved
  target (`host:port -> localhost:local_port`) and the chosen intermediate
  host, so the operator can confirm before traffic flows.
- When the user requests a tunnel by name but that name is not declared
  under the target Service in the Manifest, the system shall fail with an
  explicit "no such tunnel" error.
- When the user requests a tunnel without naming one, and more than one
  tunnel is declared across the Manifest, the system shall list all
  declared tunnels (name, target, target port, local port) for numbered
  selection.

Prerequisites
-------------

- The system shall document, and check where feasible, environment
  prerequisites for each transport: a working SSH client and key access for
  SSH-based exec/tunnel-through-bastion; the SSM Session Manager plugin for
  SSM-based exec/tunnel; network reachability from the operator's machine
  to AWS APIs.

Command Surface
================

.. list-table::
   :header-rows: 1
   :widths: 20 35 30 15

   * - Command
     - Arguments / Flags
     - Effect
     - Exit codes
   * - ``ssh <target>``
     - ``target`` (Service/Task identifier); ``--choose``; ``--verbose``
     - Opens an interactive SSH session to a Cluster Node backing
       ``target``. Unavailable for Fargate-backed targets.
     - ``0`` clean session end; ``1`` no SSH-capable target found /
       Fargate target
   * - ``run <target> <command>``
     - ``target``; ``command`` (words joined as one shell command);
       ``--all``; ``--choose``; ``--verbose``
     - Runs ``command`` non-interactively via SSH on one Cluster Node (or,
       with ``--all``, every Cluster Node) backing ``target``; prints
       labeled per-node output.
     - ``0`` all targets succeeded; ``1`` no SSH-capable target /
       Fargate target; non-zero if any targeted node's command failed
       (per-node failures are reported, not silently swallowed)
   * - ``exec <target>``
     - ``target``; ``--choose``; ``--verbose``
     - Execs into a container of a running Task Run backing ``target``,
       via in-container exec if enabled, else SSH-based ``docker exec``.
     - ``0`` clean session end; ``1`` no running Task Run / Remote Exec
       unavailable for this target
   * - ``tunnel <target> <tunnel-name>``
     - ``target`` (Service identifier); ``tunnel-name``; ``--choose``;
       ``--verbose``
     - Establishes the named Bastion Tunnel declared for ``target``;
       blocks in the foreground until terminated.
     - ``0`` clean termination by user; ``1`` tunnel not declared / no
       intermediate host available
   * - ``tunnel [tunnel-name]``
     - ``tunnel-name`` optional; ``--choose``; ``--verbose``
     - Top-level form: establishes any declared tunnel by name, or
       prompts with a list of all declared tunnels across the Manifest
       when omitted.
     - ``0`` clean termination by user; ``1`` no tunnels declared /
       named tunnel not found

Open Questions
===============

- Whether "Intermediate Host" should be promoted into `context.rst` as a
  first-class glossary term, or stays as spec-local vocabulary here.
- Whether the rebuild should keep supporting the literal-SSH bastion
  strategy at all, or standardize entirely on SSM Session Manager (the old
  tool supports both; SSM removes the bastion-host provisioning
  requirement and the SSH-key distribution problem).
- Exact selection rule for "choose automatically" (old behavior picks the
  first result of an AWS API list call, which is not a stable/documented
  order) — the rebuild should specify a deterministic rule (e.g. lexical
  sort by node id) rather than inheriting an unspecified one.
