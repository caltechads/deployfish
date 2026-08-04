=============
Extensibility
=============

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

Core behavior — Manifest parsing, Cluster/Service/Task lifecycle, Secret
Bindings, Bastion Tunnels — must stay small and dependency-free. Everything
that is optional, site-specific, or depends on a third-party integration
(chat notifications, message queues, an auxiliary datastore bootstrap)
belongs in an Extension instead: a self-contained, independently
installable unit of added behavior that plugs into the tool without the
core knowing about it in advance. This keeps the core CLI's dependency
footprint fixed regardless of how many integrations a given team enables.

Concepts
========

- **Extension** (existing glossary term) — this document defines its
  contract in full: how one is packaged, discovered, enabled, and how it
  attaches to core behavior.
- **Extension Hook Point** *(new term, proposed)* — a named moment in the
  command lifecycle (e.g. "after a Service's Workload Definition is
  updated") that an Extension may attach a callback to. See Open Questions.

Behavior
========

Packaging and discovery
------------------------

- An Extension SHALL be an independently installable Python package.
- An Extension SHALL declare itself to the core tool via a package-level
  entry point group dedicated to this tool, so the core can enumerate
  installed Extensions without importing them first.
- WHERE an Extension package is installed but not declared enabled in the
  Manifest or tool configuration, the tool SHALL NOT load or execute it.

Enabling and configuring
-------------------------

- The tool's configuration SHALL support a per-Extension configuration
  block, keyed by the Extension's name, holding at minimum an `enabled`
  flag and any Extension-specific settings (e.g. a notification channel,
  a queue name, credentials reference).
- WHEN an Extension's `enabled` flag is not true, the tool SHALL treat it
  as disabled even if the underlying package is installed.
- WHEN the same Extension is referenced in more than one configuration
  source, the tool's own configuration SHALL take precedence over the
  Extension's own defaults.

Attaching to core behavior
----------------------------

- The tool SHALL expose a fixed set of Extension Hook Points, each fired
  at a specific lifecycle moment, at minimum:

  - before a new object (Service, Task, or similar) is created
  - after a new object is created
  - before an existing object is updated (i.e. before a Deployment
    Rollout begins)
  - after an existing object is updated (i.e. after a Deployment Rollout
    completes or fails)
  - before an object is deleted
  - after an object is deleted
  - before a Service's running count is changed
  - after a Service's running count is changed
  - during tool startup, before the Manifest is parsed (to let an
    Extension inject or transform Manifest content)

- An Extension SHALL register one callback per Hook Point it cares about;
  Hook Points it does not register for SHALL have no effect on it.
- WHEN a Hook Point fires, the tool SHALL pass it the relevant domain
  object (e.g. the Service being updated) and, for post-update points,
  whether the operation succeeded and a failure reason if not.
- Multiple Extensions MAY register callbacks on the same Hook Point; the
  tool SHALL run all of them.

Failure isolation
------------------

- WHEN an Extension's callback raises an exception, the tool SHALL log the
  failure and continue; an Extension failure SHALL NOT roll back or block
  the underlying operation it observed, because Extension callbacks are
  by design observers/side-effects, not participants in the operation's
  success criteria.
- IF an Extension needs to block or gate an operation (rather than merely
  react to it), that is a distinct capability not covered by the observer
  Hook Points above — see Open Questions.

Reference Extensions
----------------------

These illustrate the contract; they are not part of the core:

- **Notification Extension** (chat notification on deploy): registers a
  callback on the "after object update" Hook Point. WHEN the updated
  object is a Service and the update succeeded, it composes a formatted
  message (service name, environment, deployer, changelog since last
  deploy) and posts it to a configured channel. WHEN the update failed,
  it SHALL take no action.
- **Message Queue Extension** (deploy-event fan-out): registers the same
  "after object update" Hook Point. WHEN the updated object is a Service
  and the update succeeded, it publishes a structured deploy-event message
  (service, environment, description, timestamp) to one or more configured
  queues. WHEN no queues are configured, it SHALL report a clear
  configuration error rather than silently doing nothing.
- **Auxiliary Datastore Extension** (e.g. bootstrapping a MySQL database
  alongside a Service): contributes its own CLI subcommands (e.g. to
  create a database, run a client shell against it via a Bastion Tunnel)
  and registers on the "before Manifest is parsed" Hook Point to let
  Manifest authors declare a new kind of Resource Reference (a database
  instance) inline. This is the pattern for an Extension that adds command
  surface and Manifest vocabulary, not just observes lifecycle events.

Command Surface
================

.. list-table::
   :header-rows: 1

   * - Surface
     - Shape
     - Effect
   * - Tool configuration: ``extension.<name>.enabled``
     - boolean
     - Enables/disables a discovered Extension by name.
   * - Tool configuration: ``extension.<name>.*``
     - Extension-defined
     - Extension-specific settings (channel, queue list, credentials
       reference, etc.), namespaced under the Extension's name.
   * - Extension-contributed subcommands
     - Extension-defined
     - An enabled Extension MAY register additional top-level CLI
       subcommands under its own name; the core tool does not constrain
       their shape beyond standard exit-code conventions (see
       :doc:`00-overview`).

Open Questions
===============

- Should "Extension Hook Point" be promoted into ``context.rst`` as a
  first-class glossary term? Recommend yes once a second spec needs to
  reference it (e.g. :doc:`03-ecs-service-lifecycle` naming the exact
  create/update/delete/scale points this spec generalizes from).
- The old implementation's observer-only hooks cannot block or veto an
  operation (e.g. an Extension can't refuse a Deployment Rollout). Is a
  gating/veto capability in scope for the rebuild, or deliberately out of
  scope to keep Extensions side-effect-only? Recommend deliberately out of
  scope — keeps failure isolation simple and matches observed usage (all
  three reference Extensions are pure observers).
- Manifest-injecting Extensions (the auxiliary-datastore pattern) blur the
  line between "Extension" and "core Manifest schema." Recommend the
  rebuild require such Extensions to use a clearly namespaced Manifest
  section (e.g. under an `extensions:` key) rather than injecting
  top-level keys, to avoid schema collisions — needs confirmation.
