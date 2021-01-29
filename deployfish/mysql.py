import os
import subprocess
import tempfile


class MySQLDatabaseManipulator(object):

    def __init__(self):
        self.db_config = {
            "name": os.environ.get('DB_NAME', ''),
            "user": os.environ.get('DB_USER', ''),
            "host": os.environ.get('DB_HOST', ''),
        }
        os.environ["MYSQL_PWD"] = os.environ.get('DB_PASSWORD', '')

    def dump_db(self):
        cmd = [
            "mysqldump",
            "-u%(user)s" % self.db_config,
            "-h%(host)s" % self.db_config,
            "--opt",
            "%(name)s" % self.db_config,
        ]
        filename = "%(name)s.sql" % self.db_config
        with open(filename, 'w') as outfile:
            subprocess.call(cmd, stdout=outfile)
            outfile.close()
        return filename

    def compress_db_dump(self, filename):
        cmd = ["gzip", filename]
        subprocess.call(cmd)
        return "%s.gz" % filename

    def _run_mysql_cmd(self, command, db=None):
        cmd = [
            "mysql",
            "-u%(user)s" % self.db_config,
            "-h%(host)s" % self.db_config,
            "-e %s" % command
            ]
        if db:
            cmd.append("%(name)s" % self.db_config)
        subprocess.call(cmd)

    def _load_mysql_file(self, filename, db=None):
        self._run_mysql_cmd("source %s" % filename, db)

    def empty_db(self):
        cmd = [
            "mysqldump",
            "-u%(user)s" % self.db_config,
            "-h%(host)s" % self.db_config,
            "--add_drop-table",
            "--no-data",
            "%(name)s" % self.db_config,
        ]

        tmphandle, tmppath = tempfile.mkstemp(text=True)
        tmpfile = os.fdopen(tmphandle, "w")

        sql_data = subprocess.check_output(cmd, stderr=None).split('\n')
        tmpfile.write("SET FOREIGN_KEY_CHECKS = 0;\n")
        tmpfile.write("use %(name)s;\n" % self.db_config)
        for line in sql_data:
            if line.startswith("DROP"):
                tmpfile.write(line + '\n')
        tmpfile.close()
        self._run_mysql_cmd("source %s" % tmppath)
        os.remove(tmppath)

    def load_compressed_db_dump(self, filename):
        cmd = ["gunzip", filename]
        # strip the '.gz'
        sqlfile = filename[:-3]
        subprocess.call(cmd)
        self._load_mysql_file(sqlfile, self.db_config["name"])
