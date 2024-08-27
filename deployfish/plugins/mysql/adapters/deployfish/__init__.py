from deployfish.registry import importer_registry as registry

from .mysql import MySQLDatabaseAdapter


# -----------------------
# Adapter registrations
# -----------------------

# mysql
registry.register('MySQLDatabase', 'deployfish', MySQLDatabaseAdapter)
