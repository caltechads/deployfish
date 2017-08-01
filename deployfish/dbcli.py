#!/usr/bin/env python
import os

from deployfish.mysql import MySQLDatabaseManipulator
from deployfish.aws.s3 import S3


def dump():
    dbm = MySQLDatabaseManipulator()
    dbdump = dbm.dump_db()
    dbzipfile = dbm.compress_db_dump(dbdump)
    S3().put_file(dbzipfile)
    os.remove(dbzipfile)


def load():
    s3m = S3()
    s3m.get_file(dbzipfile)
    dbm = MySQLDatabaseManipulator()
    dbdump = dbm.dump_db()
    dbzipfile = dbm.compress_db_dump(dbdump)
    os.remove(dbzipfile)
