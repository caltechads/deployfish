import yaml
import re
import os
import os.path

from deployfish.terraform import Terraform


class Config(object):

    """
    This class reads our ``deployfish.yml`` file and handles the allowed
    variable substitutions in string values for service entries under the
    ``services:`` section.

    Allowed variable substitutions:

    * ``${terraform.<lookup key>}``:  If we have a ``terraform:`` section
      in our YAML, replace this with the terraform lookup value for
      ``<lookup key>``.

    * ``${env.<environment var>}```:  If the environment variable
      ``<environment var>`` exists in our environment, replace this with
      the value of that environment variable.
    """

    TERRAFORM_RE = re.compile('\$\{terraform.(?P<key>[A-Za-z0-9_]+)\}')
    ENVIRONMENT_RE = re.compile('\$\{env.(?P<key>.+)\}$')

    def __init__(self, filename='deployfish.yml', env_file=None, interpolate=True):
        self.__raw = self.load_config(filename)
        self.env_file = env_file
        self.environ = None
        self.terraform = None
        if interpolate:
            if 'terraform' in self.__raw:
                self.terraform = Terraform(yml=self.__raw['terraform'])
            else:
                self.terraform = None
            self.replace()

    def load_config(self, filename):
        with open(filename) as f:
            return yaml.load(f)

    def load_env_file(self, env_file):
        if env_file and os.path.isfile(env_file):
            lines = []
            with open(env_file) as f:
                lines = f.readlines()
                # Strip the comments and empty lines
                lines = [x.strip() for x in lines if x.strip() and not x.strip().startswith("#")]
            for line in lines:
                # split on the first "="
                parm = str.split(line, '=', 1)
                if len(parm) == 2:
                    key = parm[0]
                    value = parm[1]
                    self.environ[key] = value

    def replace(self):
        """
        Do variable replacement in all strings in the YAML data for
        each listed services under the ``services:`` section.
        """
        for service in self.__raw['services']:
            replacers = {
                'environment': service.get('environment', 'prod'),
                'service-name': service['name'],
                'cluster-name': service['cluster']
            }
            self.environ = {}
            if 'env_file' in service:
                self.load_env_file(service['env_file'])
            if self.env_file:
                self.load_env_file(self.env_file)
            # else:
            #     self.environ = os.environ

            self.__do_dict(service, replacers)

    def __replace(self, raw, key, value, replacers):
        if isinstance(value, dict):
            self.__do_dict(value, replacers)
        elif any(isinstance(value, t) for t in (list, tuple)):
            self.__do_list(value, replacers)
        elif isinstance(value, str):
            self.__do_string(raw, key, value, replacers)

    def __env_replace(self, key, replacers):
        envkey = key.format(**replacers).upper().replace('-', '_')
        value = self.environ.get(envkey, envkey)
        return value

    def __do_string(self, raw, key, value, replacers):
        if self.terraform:
            m = self.TERRAFORM_RE.search(value)
            if m:
                raw[key] = self.TERRAFORM_RE.sub(self.terraform.lookup(m.group('key'), replacers), value)
                value = raw[key]
        m = self.ENVIRONMENT_RE.search(value)
        if m:
            # TODO: using __env_replace here is risky because of {service-name}
            # and {cluster-name}.  If these have a `-` or a '.' in them, the
            # environment variable name will be treated strangely by the shell
            # or just rejected.
            #
            # In each replacer, we should be replacing [.- ] with _ and then
            # uppercasing the result.
            raw[key] = self.ENVIRONMENT_RE.sub(self.__env_replace(m.group('key'), replacers), value)

    def __do_list(self, raw, replacers):
        for i, value in enumerate(raw):
            self.__replace(raw, i, value, replacers)

    def __do_dict(self, raw, replacers):
        for key, value in raw.items():
            self.__replace(raw, key, value, replacers)

    def get_service(self, service_name):
        """
        Get the full config for the service named ``service_name`` from our
        parsed YAML file.

        :param service_name: the name of an ECS service listed in our YAML file under the ``services:`` section
        :type service_name: string

        :rtype: dict
        """
        for service in self.__raw['services']:
            if service['name'] == service_name:
                return service
            if 'environment' in service and service['environment'] == service_name:
                return service
        raise KeyError

    def get_category_item(self, category, item_name):
        """
        Get the raw values of an item in a custom category list.

        :param category: The name of the top level category to search
        :param item_name: The name of the instance of the category
        :return:
        """
        if category in self.__raw:
            for item in self.__raw[category]:
                if item['name'] == item_name:
                    return item
        raise KeyError
