===============================
One-Off and Companion Tasks
===============================

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

Not every workload is a Service. Some work is a single job: run a
database migration, execute a backfill, invoke a batch script on demand or
on a fixed schedule. This document specifies two ways to declare such work
and the runtime record produced each time it executes.

A **One-Off Task** is a fully independent unit of work: its own Workload
Definition, own Cluster placement, own Secret Bindings, declared once at
the top level of the Manifest. It exists whether or not any Service exists.

A **Companion Task** is bound to a specific Service: it reuses that
Service's Workload Definition, network configuration, and Secret Bindings,
and exists only as long as its parent Service is declared. It is how a
Service's own operational actions (run migrations before deploying new
code, trigger a cache warm) are declared next to the Service they belong
to, so they change together.

Both are launch-on-demand or launch-on-schedule; neither is kept alive or
restarted by the platform. Each execution produces a **Task Run**: an
independent record with its own ARN, placement, and exit status, decoupled
from the definition that produced it.

Concepts
========

- One-Off Task, Companion Task, Task Run — as defined in :doc:`context`.
- **Schedule**: an optional recurring-execution rule (cron or rate
  expression) attached to a One-Off Task or Companion Task, which launches
  a Task Run automatically without operator action.

Behavior
========

Declaration
-----------

- The tool shall allow a One-Off Task to be declared in the Manifest
  independently of any Service, with its own Workload Definition,
  Cluster, launch type, network configuration, and Secret Bindings.
- The tool shall allow a Companion Task to be declared as part of a
  Service's Manifest entry, identified by a command name unique within
  that Service.
- A Companion Task shall inherit its Cluster, network configuration, and
  Secret Bindings from its parent Service's Workload Definition unless the
  Manifest explicitly overrides them for that Companion Task.
- Where a Manifest entry for a One-Off Task or Companion Task includes a
  Schedule expression, the tool shall create and manage a matching
  recurring-execution rule pointed at that task's Workload Definition.

Creating and updating
----------------------

- When a Companion Task's parent Service is updated, the tool shall update
  every Companion Task belonging to that Service to match the Service's
  current Workload Definition and Manifest configuration, by default.
- The tool shall support updating a Service's Companion Tasks
  independently of updating the Service itself, producing a new Workload
  Definition revision for each Companion Task without touching the
  running Service. This is for cases such as running a migration on a new
  code revision before rolling that revision out to the Service.
- When a Companion Task is updated independently of its Service (as
  above), the tool shall report the resulting Workload Definition revision
  so the operator can reference it directly for a Task Run without going
  through the Service.
- The tool shall reject deletion of a One-Off Task as a standalone
  operation; removing one is done by removing it from the Manifest and
  letting normal reconciliation handle it.

Launching a Task Run
---------------------

- When the operator or a Schedule triggers a One-Off Task or Companion
  Task, the tool shall launch a Task Run using that task's current
  Workload Definition, Cluster, network configuration, and resolved Secret
  Bindings.
- A single trigger may launch more than one Task Run (e.g. one per
  container/host requested); the tool shall report the identity of every
  Task Run launched.
- When placement fails (e.g. no capacity, misconfigured network parameters,
  invalid task role), the tool shall surface the placement failure reason
  from the platform and shall not report the task as started.
- Where the operator requests it, the tool shall block until every Task
  Run produced by the trigger reaches a terminal (stopped) state before
  returning.
- A Task Run's success or failure is determined by its container exit
  code(s) as reported by the platform; the tool shall not itself impose
  additional success criteria.

Scheduling
----------

- The tool shall allow an existing Schedule to be enabled or disabled
  without altering the task's Workload Definition or Manifest declaration.
- Requesting enable/disable of a Schedule on a task that has no Schedule
  declared shall be rejected with a clear error, since there is nothing to
  toggle.

Command Surface
================

One-Off Task commands
----------------------

.. list-table::
   :header-rows: 1

   * - Command
     - Arguments / Flags
     - Effect
     - Exit codes
   * - task info <name>
     - ``--includes secrets``, ``--excludes events``
     - Show the current AWS state of a One-Off Task, optionally including
       resolved Secret Bindings or excluding recent scheduling events.
     - 0 success; non-zero if not found
   * - task list
     - ``--cluster-name``, ``--service-name``, ``--task-name`` (glob
       filters), ``--task-type {any,standalone,service_helper}``,
       ``--scheduled-only``, ``--all-revisions``
     - List One-Off Tasks (and optionally Companion Tasks) matching the
       filters.
     - 0 success
   * - task create <name>
     - --
     - Create a One-Off Task in AWS from its Manifest declaration. Equivalent
       to update for a task that does not yet exist.
     - 0 success; non-zero on error
   * - task delete <name>
     - --
     - Rejected: One-Off Tasks cannot be deleted as a standalone action.
     - non-zero always
   * - task enable <name>
     - --
     - Enable this task's Schedule.
     - 0 success; non-zero if no Schedule exists
   * - task disable <name>
     - --
     - Disable this task's Schedule.
     - 0 success; non-zero if no Schedule exists
   * - task run <name>
     - ``--wait``
     - Launch a Task Run from the task's current AWS state. With
       ``--wait``, block until it stops.
     - 0 success; non-zero on placement failure
   * - task plan <name>
     - --
     - Show the diff between the Manifest declaration and the task's
       current AWS state without applying it.
     - 0 success
   * - task logs tail <name>
     - ``--mark``, ``--sleep <seconds>``, ``--filter-pattern``
     - Tail this task's log stream (when its log driver supports it).
     - 0 success; non-zero if logs unsupported
   * - task logs list <name>
     - ``--limit``
     - List available log streams for this task.
     - 0 success

Companion Task commands (scoped under a Service)
--------------------------------------------------

.. list-table::
   :header-rows: 1

   * - Command
     - Arguments / Flags
     - Effect
     - Exit codes
   * - service commands info <service> <command>
     - ``--includes secrets``
     - Show the current AWS state of one Companion Task on a Service.
     - 0 success; non-zero if not found
   * - service commands list <service>
     - --
     - List all Companion Tasks declared on a Service.
     - 0 success
   * - service commands update <service>
     - --
     - Update every Companion Task on the Service independently of the
       Service itself; reports the new Workload Definition revision per
       task.
     - 0 success; non-zero on error
   * - service commands enable <service> <command>
     - --
     - Enable this Companion Task's Schedule.
     - 0 success; non-zero if no Schedule exists
   * - service commands disable <service> <command>
     - --
     - Disable this Companion Task's Schedule.
     - 0 success; non-zero if no Schedule exists
   * - service commands run <service> <command>
     - ``--wait``
     - Launch a Task Run for this Companion Task. With ``--wait``, block
       until it stops.
     - 0 success; non-zero on placement failure
   * - service commands logs tail <service> <command>
     - ``--mark``, ``--sleep``, ``--filter-pattern``
     - Tail this Companion Task's log stream.
     - 0 success
   * - service commands logs list <service> <command>
     - ``--limit``
     - List available log streams for this Companion Task.
     - 0 success

Open Questions
================

- Exact success/failure exit-code mapping for ``task run``/``service
  commands run`` when a Task Run's container exits non-zero (vs. tool-level
  placement failure) is not fully specified by the old code and should be
  pinned down: should the CLI itself exit non-zero if the *container*
  failed, or only if the platform failed to place the task? Recommend: the
  new tool should always propagate the container exit status when
  ``--wait`` is used, so `run` failures are scriptable.
- Old code shows a Companion Task command name must be unique per Service,
  but does not document any length/character restrictions. Needs a
  decision for the new Manifest schema.
- Not addressed here: how a Task Run's log destination is chosen when a
  task defines multiple containers with different log configuration —
  deferred to :doc:`07-observability`.
