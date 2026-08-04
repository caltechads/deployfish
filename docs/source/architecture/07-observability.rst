=============
Observability
=============

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

Operators need to read a workload's logs by name — "show me what the
``web`` Service is logging" or "did last night's migration Task Run
succeed?" — without first discovering an AWS CloudWatch Logs group name,
stream name, or ARN by hand. This document specifies how the tool resolves
a named Service, One-Off Task, or Companion Task down to its log source,
lists that source's log streams, and tails it live.

Only the ``awslogs`` log driver is supported, since it is the only driver
that routes container output to a CloudWatch Logs group the tool can query
by name. Any Workload Definition using another log driver cannot be tailed
by this tool and must say so clearly rather than fail silently.

Concepts
========

- **Service**, **One-Off Task**, **Companion Task**, **Task Run**,
  **Workload Definition** — as defined in :doc:`context`; this document
  adds no new canonical terms, but see Open Questions for two candidates
  the user should confirm before they're added to the glossary.

Behavior
========

Log source resolution
----------------------

- The tool shall resolve a named Service, One-Off Task, or Companion Task
  to a single CloudWatch Logs group and stream-name prefix by reading the
  ``awslogs-group`` and ``awslogs-stream-prefix`` log options recorded on
  that object's Workload Definition, without requiring the user to supply
  either value.
- When the resolved Workload Definition's log driver is not ``awslogs``,
  the tool shall raise an error naming the actual log driver and shall not
  attempt to query CloudWatch Logs.
- The tool shall determine the "current" log stream for a Service or Task
  by listing the log group's streams under the resolved prefix and
  selecting the most recently created one; it shall not require the user
  to supply a specific stream name for the common case.

Listing
-------

- When a user lists log streams for a resolved log source, the tool shall
  return them ordered newest-created-first.
- The tool shall support limiting the number of streams returned.
- The tool shall support listing CloudWatch Logs groups and streams
  directly by group name, independent of any Service or Task, for cases
  where the operator already knows the AWS-side name.

Tailing
-------

- When a user tails a Service, One-Off Task, or Companion Task, the tool
  shall poll the resolved log group for new events at a configurable
  interval (default 10 seconds) and print each new event's timestamp and
  message to standard output in arrival order.
- The tool shall begin tailing from the last event timestamp of the most
  recent existing stream at the time tailing starts, so that it does not
  replay a workload's entire log history by default.
- The tool shall support restricting tailed events to those matching a
  CloudWatch Logs filter pattern.
- The tool shall support restricting tailed events to streams whose name
  matches a given prefix, for log sources with multiple concurrent
  streams.
- While tailing, the tool shall optionally print a visible marker line at
  each poll interval (opt-in flag) so the operator can distinguish "no new
  output" from "the tail has stopped."
- The tool shall continue tailing indefinitely until interrupted by the
  user; it shall not exit on its own when a workload stops producing
  output.
- When no log stream yet exists for a resolved log source (e.g. the
  workload has never started), the tool shall report this plainly rather
  than raising an unhandled error, and shall begin tailing from the point
  the first stream appears if the user leaves the tail running.

Command Surface
================

.. list-table::
   :header-rows: 1
   :widths: 30 35 25 10

   * - Command
     - Arguments / Flags
     - Effect
     - Exit Codes
   * - ``logs service <name>``
     - ``--mark``, ``--sleep <seconds>`` (default 10), ``--filter-pattern <pattern>``, ``--stream-prefix <prefix>``
     - Resolve the named Service's Workload Definition to its log group/prefix and tail it live.
     - 0 success; 1 unknown Service; 2 log driver is not ``awslogs``
   * - ``logs task <pk>``
     - ``--mark``, ``--sleep <seconds>``, ``--filter-pattern <pattern>``
     - Tail a One-Off Task's Task Run logs by the Task Run's primary key.
     - 0 success; 1 unknown Task Run; 2 log driver is not ``awslogs``
   * - ``logs command <service-name> <command>``
     - ``--mark``, ``--sleep <seconds>``, ``--filter-pattern <pattern>``
     - Tail a Companion Task's ("command") logs, scoped to a specific named command on a Service.
     - 0 success; 1 unknown Service or command name; 2 log driver is not ``awslogs``
   * - ``logs group list``
     - ``--prefix <prefix>``
     - List CloudWatch Logs groups directly by name/prefix, independent of any Service or Task.
     - 0 success; 1 no matching groups
   * - ``logs group tail <group-name>``
     - ``--mark``, ``--sleep <seconds>``, ``--filter-pattern <pattern>``, ``--stream-prefix <prefix>``
     - Tail a CloudWatch Logs group directly by AWS-side name.
     - 0 success; 1 unknown group
   * - ``logs stream list <group-name>``
     - ``--prefix <prefix>``, ``--limit <n>``
     - List log streams within a named group, newest-created-first.
     - 0 success; 1 unknown group
   * - ``logs stream tail <group-name>:<stream-name>``
     - ``--mark``, ``--sleep <seconds>``
     - Tail one specific log stream directly by its composite id.
     - 0 success; 1 unknown stream

Open Questions
===============

- **Per-container log routing.** The old implementation reads a single
  ``logging`` configuration off the whole Workload Definition, implying
  one log driver/group/prefix per Task even when a Task has multiple
  Container Specs. Confirm whether the rebuild should support distinct
  log destinations per Container Spec (multi-container tailing/labeling by
  container name), or keep the one-log-source-per-task simplification.
- **New term candidates** — not yet in the glossary, need your
  confirmation before use elsewhere: "Log Source" (the resolved
  group+prefix pair a Service/Task/command tails from) and "Companion Task
  Command" (the name used to select which Companion Task on a Service to
  tail — currently called just "command" above). Recommend adding both to
  ``context.rst`` if this document's usage is approved.
