import json
import os
import os.path
import requests

import boto3
from botocore.exceptions import ClientError

from deployfish.aws import get_boto3_session


class NoSuchStateFile(Exception):
    pass


class Terraform(dict):
    """
    This class allows us to retrieve values from our terraform state file.
    """

    def __init__(self, yml=None):
        self.load_yaml(yml)

    def _get_state_file_from_s3(self, config):
        state_file_url = config['statefile']
        if 'profile' in config:
            session = boto3.session.Session(
                profile_name=config['profile'],
                region_name=config.get('region', None),
            )
        else:
            session = get_boto3_session()
        s3 = session.resource('s3')
        parts = state_file_url[5:].split('/')
        bucket = parts[0]
        filename = "/".join(parts[1:])
        key = s3.Object(bucket, filename)
        try:
            state_file = key.get()["Body"].read().decode('utf-8')
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'NoSuchKey':
                raise NoSuchStateFile("Could not find Terraform state file {}".format(state_file_url))
            else:
                raise ex
        return json.loads(state_file)

    def get_terraform_state(self, state_file_url):
        tfstate = self._get_state_file_from_s3(state_file_url)
        major, minor, patch = tfstate['terraform_version'].split('.')
        if int(minor) >= 12:
            for key, value in tfstate['outputs'].items():
                self[key] = value
        else:
            for i in tfstate['modules']:
                if i['path'] == [u'root']:
                    for key, value in i['outputs'].items():
                        self[key] = value

    def load_yaml(self, yml):
        self.get_terraform_state(yml)
        self.lookups = yml['lookups']

    def lookup(self, attr, keys):
        return self[self.lookups[attr].format(**keys)]['value']


class TerraformE(dict):

    def __init__(self, yml, api_token=None):
        if api_token is None:
            if 'ATLAS_TOKEN' in os.environ:
                self.api_token = os.getenv('ATLAS_TOKEN')
            else:
                print("No Terraform Enterprise API token provided!")
        else:
            self.api_token = api_token

        self.organization = ''
        self.workspace = ''
        self.api_end_point = 'https://app.terraform.io/api/v2'

        self.load_yaml(yml)

    def load_yaml(self, yml):
        self.workspace = yml['workspace']
        self.organization = yml['organization']
        self.lookups = yml['lookups']
        self.list_state_versions()

    def list_state_versions(self):
        end_point = self.api_end_point + "/state-versions?"
        org_filter = "filter[organization][name]=" + self.organization
        workspace_filter = "filter[workspace][name]=" + self.workspace

        web_request = end_point + org_filter + "&" + workspace_filter

        headers = {'Authorization': 'Bearer ' + self.api_token,
                   'Content-Type': 'application/vnd.api+json'}
        response = requests.get(web_request, headers=headers)
        data = json.loads(response.text)
        state_download_url = data['data'][0]['attributes']['hosted-state-download-url']

        self.get_terraform_state(state_download_url)

    def get_terraform_state(self, state_download_url):
        response = requests.get(state_download_url)
        tfstate = json.loads(response.text)
        for i in tfstate['modules']:
            if i['path'] == [u'root']:
                for key, value in i['outputs'].items():
                    self[key] = value

    def lookup(self, attr, keys):
        return self[self.lookups[attr].format(**keys)]['value']
