---
status: accepted
---

# Add a `deployfish postgres` plugin mirroring `deployfish mysql`

`deployfish` ships a `mysql` plugin (`deployfish/plugins/mysql/`) that manages databases and
users on remote MySQL/RDS-MySQL servers over SSH: `info`, `create`, `update`, `validate`,
`dump`, `load`, `show-grants`, `server-version`. We're adding a parallel `postgres` plugin
(`deployfish/plugins/postgres/`) exposing the identical command set for PostgreSQL/RDS
Postgres targets, built by reusing the mysql plugin's cement controller/model/adapter/hooks
structure verb-for-verb, not by inventing a new shape.

The postgres plugin targets PostgreSQL 18.6 only. Mysql's `create`/`update` SQL branches on
`major_server_version` (5.6 vs 8.0 auth syntax); postgres has no equivalent branch -- there is
exactly one SQL path for `create` and one for `update`. `server-version` is retained purely as
an informational command, not as a decision input anywhere else in the plugin.

Config shape mirrors `mysql:` exactly: a new `postgres:` top-level `deployfish.yml` section,
a list of dicts (`name`, `service`, `host`, `db`, `user`, `pass`, `port` optional), values
optionally referencing `config.KEY` to resolve through the owning service's AWS SSM secrets,
via the same `pre_config_interpolate` hook mechanism (`add_processable_section("postgres")`).
There are no implicit/default database names, usernames, hosts, or passwords -- every
connection's identity must be explicit in `deployfish.yml`, same as mysql. The `character_set`
key is retained and maps to `ENCODING` on `CREATE DATABASE` (default `'UTF8'`). Mysql's
`collation` key is dropped entirely: postgres collation must match the template database's
locale, so exposing it as a static per-connection default invites `CREATE DATABASE` failures
rather than working the way mysql's `COLLATE` clause does. `ENCODING` carries the same class
of risk in principle (`CREATE DATABASE` also fails if the requested encoding is incompatible
with the template database's locale) -- it's kept anyway because stock RDS Postgres ships
`template1` as UTF8, making `ENCODING 'UTF8'` reliable in practice, whereas an arbitrary
caller-supplied `collation` has no such reliable default to fall back on. This is a
difference in failure probability, not a difference in failure mechanism.

`create` issues `CREATE ROLE {user} LOGIN PASSWORD '{pass}';` and `CREATE DATABASE {db} OWNER
{user} ENCODING '{character_set}';` against the `postgres` maintenance database as **two
separate `psql -c` invocations**, not one semicolon-joined command string. When multiple
statements are sent as a single query-protocol message, PostgreSQL implicitly wraps them in
one transaction block, and `CREATE DATABASE` cannot run inside a transaction block --
combining it with `CREATE ROLE` in one `-c` string fails with `ERROR: CREATE DATABASE cannot
run inside a transaction block`. Mysql's client has no equivalent restriction, so this is a
genuine divergence forced by Postgres semantics, not a style choice: mirroring mysql's
"one joined command" pattern here would ship a broken `create`. No additional `GRANT` is
needed at create time: PostgreSQL 15+ grants the database owner rights on the database's
`public` schema via the built-in `pg_database_owner` role, so `OWNER {user}` alone is
sufficient -- **provided the target RDS instance's `template1` still carries PG15's default
`public`-schema ACL for `pg_database_owner`**, true for stock/unmodified RDS Postgres 15+ but
an environmental assumption, not a language guarantee; a hand-modified `template1` would make
`create` succeed while leaving `{user}` without usable schema access, surfacing later as a
permission-denied on first query rather than as a `create`-time failure. `update` runs `ALTER ROLE
{user} WITH PASSWORD '{pass}'; GRANT ALL PRIVILEGES ON DATABASE {db} TO {user}; GRANT ALL ON
SCHEMA public TO {user};`, also against the `postgres` maintenance db (`ALTER ROLE`/`GRANT ON
DATABASE` don't require connecting to the target db). `update` has no encoding-change
capability, matching reality rather than mysql's behavior: postgres `ENCODING` is immutable
after `CREATE DATABASE`, so there is no `ALTER DATABASE ... ENCODING` equivalent to attempt.

`validate` and `server-version` run against the `postgres` maintenance db too, using `psql -t
-A` (tuples-only, unaligned output) for a single clean output line. `server-version` actually
parses this output (mirroring mysql's `major_server_version()`/`server_version()`); `-t -A`
replaces mysql's fragile table-output line-slicing (`output.split("\n")[3][2:-2]`), which
depends on `mysql`'s specific ASCII-table rendering and has no clean postgres equivalent to
port. `validate`, like its mysql counterpart, never parses its command's output at all -- it
only checks the command's exit status -- so `-t -A` there is purely for tidier `--verbose`
display, not a parsing requirement. `show-grants` runs `psql -c "\du+ {user}"` -- a
role-attributes listing, not a full `information_schema` privilege query. This is intentionally
lower-fidelity than mysql's `SHOW GRANTS;` (which lists the exact per-object grants); postgres
has no single-statement equivalent, and `\du+` answers the same practical question ("what can
this role do") without building and maintaining a privilege-scanning query.

`dump`/`load` use plain-SQL format only (`pg_dump --format=plain`, loaded via `psql
--file={filename}`), not `pg_dump`'s custom/binary format. This preserves mysql's flat `.sql`
file behavior exactly, including the filename-collision retry sequence (`{service}.sql`,
`{service}-1.sql`, ...) -- a deliberate rejection of `pg_restore`-based custom-format dumps,
which would break diffability and require a second tool to load. Unlike the maintenance-db
commands above, `dump`/`load` connect to the real target database (`--dbname={obj.db}`), since
it necessarily exists by the time either command runs.

Postgres client tools have no `--password=` flag; non-interactive auth uses a `PGPASSWORD=
'{password}'` env-var prefix on the remote command string. This carries the same
inline-in-argv password-visibility tradeoff mysql's `--password='{password}'` already has --
not a new regression, just postgres's non-interactive idiom.

Mysql hardcodes absolute binary paths (`/usr/bin/mysql`, `/usr/bin/mysqldump`), assuming a
fixed remote filesystem layout. The postgres plugin does not: our deployment containers run a
variety of Linux distributions where `psql`/`pg_dump` aren't guaranteed to live at
`/usr/bin/`. Commands invoke bare `psql`/`pg_dump`, resolved off the remote `$PATH` over SSH.
Consequently, the plugin must detect a "command not found" failure for either binary and raise
a specific, actionable error identifying which binary is missing on the remote host -- not
let a raw shell "command not found" or a generic `OperationFailed` reach the user unexplained.
This is a deliberate divergence from mysql's approach, driven by our actual fleet's
heterogeneity, not an oversight to reconcile later.

Root/master credentials reuse `RDSInstance.root_user` / `.root_password` / `.secret_enabled`
unchanged -- confirmed engine-agnostic (no `mysql`-specific branching in `rds.py`), so
`create`/`update` resolve the master instance the same way mysql's controller does
(`db_instance_name = obj.host.split(".")[0]`, `RDSInstance.objects.get(db_instance_name)`).

Naming is `PostgresDatabase` / `PostgresDatabaseManager` / `PostgresDatabaseAdapter`,
`postgres` as the config section and controller label, `deploy postgres <verb>` as the CLI,
`plugin.postgres: enabled: true` as the config toggle -- one consistent term throughout, no
`pg`/`psql` abbreviation anywhere in a class, section, or command name.

Plugin loading requires no new wiring. mysql's own plugin-loading path was independently
verified at runtime rather than assumed: instantiating `DeployfishApp` and inspecting
`app.plugin` after `app.setup()` shows the *active* plugin handler is cement's built-in
`CementPluginHandler`, not deployfish's `DeployfishCementPluginHandler`
(`deployfish/ext/ext_df_plugin.py`) -- that handler is registered but never made active (no
`plugin_handler` `Meta` override selects it), making it dead code. Cement's built-in handler
defaults `plugin_module` to `f"{app.label}.plugins"` = `"deployfish.plugins"` and
auto-discovers/loads every submodule there by convention; `mysql`, `slack`, and `sqs` already
load this way with zero explicit registration. Dropping `deployfish/plugins/postgres/` with a
`load(app)` function is therefore sufficient on its own -- no `pyproject.toml` entry-points
section, and no `main.py` changes, are needed or wanted.

Non-goal: no shared base class or abstraction merging the mysql and postgres models. This ADR
treats them as parallel, independently-evolving plugins. A sample size of two engines with
materially different auth (`--password=` vs `PGPASSWORD`), grant (implicit `GRANT ALL ON *`
vs `pg_database_owner`), and encoding (mutable `ALTER DATABASE CHARACTER SET` vs immutable
`ENCODING`) models is not enough evidence to justify a shared abstraction; forcing one now
would mean guessing at a seam neither engine has actually forced yet.

## Considered Options

- Send `CREATE ROLE ...; CREATE DATABASE ...;` as one semicolon-joined `psql -c` string,
  mirroring mysql's single-command style exactly -- rejected: PostgreSQL implicitly wraps a
  multi-statement query-protocol message in one transaction block, and `CREATE DATABASE`
  cannot run inside a transaction block; this would make `create` fail every time it runs,
  not just in some edge case.
- Make `create` idempotent (`CREATE ROLE ... IF NOT EXISTS`-equivalent, or check-then-create)
  -- rejected for this pass: mysql's own `create` isn't idempotent either (no `IF NOT EXISTS`
  on either version branch); adding idempotency only on the postgres side would be an
  unrequested behavior difference between the two plugins, not parity.
- Hardcode `/usr/bin/psql`/`/usr/bin/pg_dump`, matching mysql's own hardcoded paths exactly --
  rejected: our containers run varied Linux distros where those tools aren't guaranteed to sit
  at `/usr/bin/`; mysql's assumption is known to be fragile, not a pattern worth repeating.
- Custom/binary-format `pg_dump` (`--format=custom`, restored via `pg_restore`) -- rejected:
  breaks symmetry with mysql's diffable flat-`.sql`-file model and the existing
  filename-collision-retry behavior, and adds a second required remote tool.
- Full `information_schema`-based privilege query for `show-grants` -- rejected: `\du+ {user}`
  answers the same practical question with no query to maintain, matching mysql's one-liner
  simplicity; full per-object grant fidelity wasn't asked for.
- Carry `collation` over from mysql as a static per-connection default -- rejected: postgres
  collation must match the template database's locale; a static default would intermittently
  fail `CREATE DATABASE` rather than behave like mysql's `COLLATE` clause.
- Support multiple PostgreSQL major versions via version-branched SQL, mirroring mysql's
  5.6-vs-8.0 split -- rejected: no current need for anything but 18.6, and inventing a branch
  with only one real arm is speculative generalization.
- A shared `SQLDatabase`/`RelationalDatabase` base class for mysql and postgres models --
  rejected as premature: the two engines diverge enough in auth, grants, and encoding
  semantics that a forced shared abstraction would be guessed, not derived from evidence.
- Register `postgres` via `pyproject.toml` `deployfish.plugins` entry-points, believing that
  was the live loading mechanism -- rejected after runtime verification: the active plugin
  handler is cement's built-in convention-based one, and adding an unused entry-points section
  would be inert config, not real wiring.
