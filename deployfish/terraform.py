import json
import os.path

import boto3


class Terraform(dict):
    """
    This class allows us to retrieve values from our terraform state file.
    """

    def __init__(self, yml):
        self.load_yaml(yml)

    def _get_state_file_from_s3(self, state_file_url):
        s3 = boto3.resource('s3')
        key = s3.Object(os.path.dirname(state_file_url)[5:], os.path.basename(state_file_url))
        state_file = key.get()["Body"].read().decode('utf-8')
        return json.loads(state_file)

    def get_terraform_state(self, state_file_url):
        tfstate = self._get_state_file_from_s3(state_file_url)
        for i in tfstate['modules']:
            if i['path'] == [u'root']:
                for key, value in i['outputs'].items():
                    self[key] = value

    def load_yaml(self, yml):
        self.get_terraform_state(yml['statefile'])
        self.lookups = yml['lookups']

    def lookup(self, attr, keys):
        return self[self.lookups[attr].format(**keys)]['value']
