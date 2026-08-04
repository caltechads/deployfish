=====================
Configuration Model
=====================

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

The Manifest is the single source of truth a Service owner or operator
writes and version-controls to describe every Cluster, Service, and Task
the tool should manage. It must be readable by a human reviewing a pull
request, safely re-runnable (loading it twice with no external changes
produces the same result), and able to pull environment-specific values
(hostnames, ARNs, account IDs) from outside itself so the same Manifest
shape can be reused across environments without hand-editing per
environment.

Concepts
========

- Manifest
- Manifest Interpolation
- Resource Reference

Behavior
========

Structure
---------

- The system shall load the Manifest from a default filename in the
  current working directory when no path is given, and shall accept an
  explicit path override via a command-line flag or environment variable.
- The system shall parse the Manifest as YAML and shall treat a missing
  or unreadable Manifest file as a fatal error, printing a clear message
  naming the file and exiting non-zero.
- The system shall organize the Manifest into top-level sections,
  including at minimum a section listing Services, a section listing
  One-Off Tasks and Companion Tasks, and a section listing Bastion Tunnel
  definitions.
- The system shall require every entry within a section to declare a
  unique ``name`` within that section, and shall treat a missing ``name``
  on an entry as a fatal validation error.
- Where an entry declares an ``environment`` label, the system shall
  accept that label as an alternate lookup key equivalent to ``name`` for
  commands that select a single entry.
- When two entries in the same section share the same ``environment``
  label, the system shall resolve a lookup by that label to the first
  matching entry in file order.
- The system shall support a global configuration section, separate from
  the per-resource sections, for tool-wide settings (e.g. which remote
  access mechanism to use for Bastion Tunnels).

Manifest Interpolation
-----------------------

- The system shall perform Manifest Interpolation only on Manifest
  sections that are declared interpolatable (Services, Tasks, and Tunnels
  at minimum), and shall leave other sections (e.g. the interpolation
  sources themselves) unprocessed.
- The system shall support environment-variable interpolation using the
  syntax ``${env.<NAME>}``, resolving ``<NAME>`` case-insensitively against
  the process environment and, where declared, a per-entry environment
  file.
- Where an entry declares its own environment file, the system shall
  prefer a value found there over the process environment when both
  define the same name.
- When an environment-variable reference cannot be resolved, the system
  shall fail Manifest Interpolation with an error identifying the section,
  entry, and unresolved name, unless the caller has explicitly requested
  missing-environment values be tolerated, in which case the system shall
  substitute a clearly-marked placeholder instead of failing.
- The system shall support infrastructure-as-code output interpolation
  using the syntax ``${terraform.<key>}``, resolving ``<key>`` against a
  declared external state source (e.g. an S3-hosted state file, or a
  Terraform Cloud/Enterprise workspace).
- The system shall support per-entry token substitution inside both the
  interpolation source path and the lookup key itself, so one interpolation
  source declaration can serve multiple entries that differ only by name,
  environment, or cluster (e.g. a state file path or lookup key containing
  a placeholder for the entry's name or environment).
- When an infrastructure-as-code lookup key is not present in the resolved
  state, the system shall fail Manifest Interpolation with an error
  identifying the section, entry, and missing key.
- The system shall cache a resolved external state source in memory for
  the duration of a single command invocation and shall not re-fetch it
  for every entry that references it, unless the resolved source location
  itself differs between entries (e.g. because of per-entry token
  substitution).
- Where an infrastructure-as-code output value is a list or mapping, the
  system shall substitute the value as a native list or mapping in the
  Manifest, not as a stringified representation.
- The system shall preserve both the pre-interpolation and
  post-interpolation form of the Manifest in memory for the duration of a
  command, so callers needing the literal author-written value (e.g. to
  redisplay it to the user) can retrieve it separately from the resolved
  value used for AWS operations.

Extensibility of the schema
----------------------------

- The system shall allow an Extension to register additional top-level
  section names as interpolatable, without requiring changes to the core
  interpolation logic.

Command Surface
================

The reference implementation had no dedicated command for validating or
rendering the Manifest independent of an AWS-facing action — Manifest
loading and Manifest Interpolation happen implicitly as a side effect of
every other command. This is flagged below as a rebuild opportunity.

.. list-table::
   :header-rows: 1

   * - Command
     - Effect
     - Exit codes
   * - (any command)
     - Loads and interpolates the Manifest before dispatching to the
       command's own logic. A load or interpolation failure short-circuits
       the command.
     - ``1`` on load/interpolation failure

Open Questions
===============

- The old tool has no standalone "validate" or "render" command for the
  Manifest — errors only surface when a specific resource command happens
  to trigger interpolation of the broken section. Recommend the rebuild
  add an explicit ``config validate`` / ``config render`` command surface;
  confirm whether that should be in scope for this rebuild or deferred.
- Precedence when both an environment file value and a process environment
  variable of the same name exist is implemented (env file wins), but the
  old docs don't state this explicitly as a guarantee — confirm this is
  the intended contract going forward, not an implementation accident.
- No maximum Manifest size, entry count, or nesting-depth limit exists in
  the old tool. Confirm whether the rebuild should impose one.
