====================
Secrets Management
====================

Terms capitalized in this document are defined in :doc:`context`.

Intent
======

Container Specs often need passwords, API keys, and other sensitive values
in their environment. The Manifest is checked into version control, so it
must never hold these values in plaintext. Instead, the Manifest declares
Secret Bindings — named references to values that live in AWS SSM
Parameter Store — and the tool is responsible for reconciling the *declared*
bindings with what actually exists in AWS, on demand, under operator
control. Nothing is pushed to AWS silently as a side effect of a Deployment
Rollout.

Concepts
========

- **Secret Binding** (owned here): a declared name/value/encryption triple
  in the Manifest, scoped to one Service or Task.
- **Secret Namespace**: the naming convention that scopes a Secret Binding
  to its owning Service/Task in Parameter Store, so bindings never collide
  across workloads. New sub-term introduced by this spec; flagged in
  :doc:`context` extension candidates below.
- **Workload Definition**, **Container Spec**, **Service**, **One-Off
  Task**, **Companion Task** — a Secret Binding belongs to the Service or
  Task that declares it and is injected into that workload's Container
  Specs at launch.

Behavior
========

Declaration
-----------

- The Manifest SHALL support declaring Secret Bindings in a ``config`` list
  scoped to a Service or Task entry, as a list of strings.
- Each entry SHALL take the form ``NAME=VALUE`` for a plaintext value.
- Each entry SHALL take the form ``NAME:secure=VALUE`` to request encryption
  with the account's default KMS key.
- Each entry SHALL take the form ``NAME:secure:<kms-key-arn>=VALUE`` to
  request encryption with a specific KMS key.
- Where the manifest value is of the form ``${env.VAR}``, the tool SHALL
  resolve VALUE via Manifest Interpolation from the local environment at
  the time the binding is written to AWS, not at deploy time.

Namespacing
-----------

- Each Secret Binding SHALL be stored in Parameter Store under a name
  prefixed with the owning Service's or Task's family name, in the form
  ``<family>.<NAME>``, so bindings for different workloads never collide.
- Listing or diffing bindings for a workload SHALL query Parameter Store by
  that workload's prefix, not by an explicit enumerated list, so bindings
  added directly in AWS outside the Manifest are still visible to the
  operator (as External Secrets, see below).

Reconciliation, not auto-push
------------------------------

- A Deployment Rollout SHALL NOT implicitly create, update, or delete
  Secret Bindings in AWS. Writing Secret Bindings SHALL be a distinct,
  explicit command.
- Before writing, the tool SHALL compute a diff between the Manifest's
  declared bindings and the current values in Parameter Store, and SHALL
  show that diff to the operator.
- When the diff is empty, the write command SHALL abort without changes
  and SHALL exit 0.
- When the diff is non-empty and the write command is invoked
  interactively, the tool SHALL require explicit operator confirmation
  before applying changes, unless a force flag is given.
- Writing SHALL create or update every Secret Binding declared in the
  Manifest for that workload, and SHALL delete any Parameter Store entry
  under that workload's prefix that is no longer declared in the Manifest,
  except entries explicitly marked as coming from outside the Manifest
  (External Secrets), which SHALL never be deleted or overwritten by this
  tool.

External Secrets
-----------------

- The tool SHALL support referencing a Secret Binding whose value is
  managed outside the Manifest entirely (created and rotated by other
  means) so it can still be diffed and shown, but SHALL treat it as
  read-only: attempting to write an External Secret SHALL fail with a
  clear error and SHALL NOT raise an AWS API call.

Resolution at launch
---------------------

- A Workload Definition whose Container Specs reference Secret Bindings
  SHALL declare an execution role with permission to read the relevant
  Parameter Store path; the tool SHALL NOT itself grant that IAM
  permission (that is a Resource Reference, provisioned outside this
  tool).
- At Task Run launch, secret values SHALL be resolved by the platform from
  Parameter Store into the container's environment; the tool never handles
  the decrypted value at deploy time for injection purposes.

Display and masking
--------------------

- Showing bindings for a workload SHALL display the current AWS value in
  the clear, since the operator explicitly requested it (SSM decrypts on
  read); the tool SHALL NOT log or persist that value anywhere besides the
  interactive command output.
- Diff output SHALL show which names are added, changed, or removed, but
  SHALL NOT print an unrelated binding's value merely because one binding
  in the same batch changed.

Error handling
--------------

- Requesting a Secret Binding by name that does not exist in Parameter
  Store SHALL fail that specific lookup with a "no secret named X exists"
  error and a non-zero exit code, without aborting a batch listing of the
  other bindings that do exist.
- A decryption failure (e.g. missing KMS permission) SHALL surface as a
  distinct, actionable error rather than a generic AWS SDK exception dump.

Command Surface
================

Every command below is scoped to a single Service or Task, addressed by
name, and is exposed under both resource types (``service`` and ``task``).

.. list-table::
   :header-rows: 1
   :widths: 20 30 35 15

   * - Command
     - Arguments / Flags
     - Effect
     - Exit codes
   * - ``<resource> secrets show <name>``
     - ``name`` (workload identifier)
     - Fetches current Secret Bindings for the workload from Parameter
       Store and prints name/value pairs, marking encrypted entries and
       their KMS key.
     - ``0`` success; non-zero if the workload or its bindings can't be
       loaded
   * - ``<resource> secrets diff <name>``
     - ``name``
     - Compares Manifest-declared bindings (excluding External Secrets)
       against current AWS values; prints an "up to date" message or a
       structured diff of additions/changes/removals.
     - ``0`` success (regardless of whether a diff was found)
   * - ``<resource> secrets write <name> [--force]``
     - ``name``; ``--force`` skips the diff-and-confirm step
     - Diffs first (unless ``--force``); on non-empty diff, prompts for
       confirmation (unless ``--force``); on confirmation, creates/updates
       declared bindings and deletes undeclared, non-external ones in AWS;
       re-displays current values afterward.
     - ``0`` success or no-op abort on empty diff; non-zero on write
       failure or declined confirmation
   * - ``<resource> secrets export <name>``
     - ``name``
     - Prints an ``.env``-formatted list of ``VAR=value`` pairs for only
       the bindings whose Manifest value was declared via
       ``${env.VAR}`` interpolation, resolved to their current AWS value —
       for regenerating a local secrets file from AWS.
     - ``0`` success; non-zero if the workload has no Secret Bindings
       support

Open Questions
===============

- Should "Secret Namespace" become a formal glossary term in
  :doc:`context`, or is it precise enough to leave as workload-prefix
  behavior described only here? Recommend adding it if
  :doc:`08-supporting-infra` or :doc:`04-standalone-tasks` need to refer to
  prefix collision rules independently.
- The old tool supports only AWS SSM Parameter Store, not AWS Secrets
  Manager, despite the glossary's Secret Binding definition mentioning
  both as a possibility. Confirm whether the rebuild should add Secrets
  Manager support or intentionally scope to Parameter Store only for v1.
- Confirm whether ``export`` (regenerating a local ``.env`` from AWS) is a
  capability worth keeping, or a workaround for a workflow the rebuild
  should solve differently (e.g. direct local secret injection for dev).
