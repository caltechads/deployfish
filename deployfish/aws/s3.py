import os
import os.path
import subprocess

from deployfish.aws import get_boto3_session


class S3(object):

    def __init__(self, source='', dest=''):
        self.config = {}
        if source:
            self.config["source"] = source
        else:
            self.config["source"] = os.environ.get('AWS_SOURCE_BUCKET', '')
        if dest:
            self.config["dest"] = dest
        else:
            self.config["dest"] = os.environ.get('AWS_DESTINATION_BUCKET', '')

    def sync_buckets(self):
        pass

    def _build_s3_url(self, filename, prefix, bucket):
        if prefix:
            full_path = "s3://%s/%s/%s" % (bucket, prefix, filename)
        else:
            full_path = "s3://%s/%s" % (bucket, filename)

        return full_path

    def _transfer_file(self, source, destination):
        cmd = [
            "aws",
            "s3",
            "cp",
            source,
            destination
        ]

        subprocess.call(cmd)

    def get_file(self, filename, prefix=None):
        source = self._build_s3_url(filename, prefix, self.config["source"])
        self._transfer_file(source, ".")

    def put_file(self, fullpath, prefix=None):
        head, filename = os.path.split(fullpath)
        dest = self._build_s3_url(filename, prefix, self.config["dest"])
        self._transfer_file(fullpath, dest)
        return dest, filename

    def put_string(self, data, key):
        s3 = get_boto3_session().client('s3')
        s3.put_object(Bucket=self.config["dest"], Key=key, Body=data)

    def delete_object(self, key):
        s3 = get_boto3_session().client('s3')
        s3.delete_object(Bucket=self.config["dest"], Key=key)
