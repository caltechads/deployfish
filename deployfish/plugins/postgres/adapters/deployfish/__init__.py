from deployfish.registry import importer_registry as registry

from .postgres import PostgresDatabaseAdapter

# -----------------------
# Adapter registrations
# -----------------------

# postgres
registry.register("PostgresDatabase", "deployfish", PostgresDatabaseAdapter)
