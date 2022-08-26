import errno
import os
import os.path
import re
from typing import Dict, Any, Union, TYPE_CHECKING

from .abstract import AbstractConfigProcessor

if TYPE_CHECKING:
    from deployfish.config import Config


class EnvironmentConfigProcessor(AbstractConfigProcessor):

    ENVIRONMENT_RE = re.compile(r'\$\{env.(?P<key>[A-Za-z0-9-_]+)\}')

    def __init__(self, config: "Config", context: Dict[str, Any]):
        super().__init__(config, context)
        self.environ: Dict[str, str] = {}
        self.per_item_environ: Dict[str, Any] = {}
        if 'env_file' in self.context:
            self.environ.update(self._load_env_file(self.context['env_file']))
        if 'import_env' in self.context and self.context['import_env']:
            self.environ.update(os.environ)

    def _load_env_file(self, filename: str) -> Dict[str, str]:
        if not filename:
            return {}
        if not os.path.exists(filename):
            if not self.context.get('ignore_missing_environment', False):
                raise self.ProcessingFailed('Environment file "{}" does not exist'.format(filename))
            return {}
        if not os.path.isfile(filename):
            if not self.context.get('ignore_missing_environment', False):
                raise self.ProcessingFailed('Environment file "{}" is not a regular file'.format(filename))
            return {}
        try:
            with open(filename, encoding='utf-8') as f:
                raw_lines = f.readlines()
        except IOError as e:
            if e.errno == errno.EACCES:
                if not self.context.get('ignore_missing_environment', False):
                    raise self.ProcessingFailed('Environment file "{}" is not readable'.format(filename))
                return {}
        # Strip the comments and empty lines
        lines = [x.strip() for x in raw_lines if x.strip() and not x.strip().startswith("#")]
        environment = {}
        for line in lines:
            # split on the first "="
            parts = str.split(line, '=', 1)
            if len(parts) == 2:
                key = parts[0]
                value = parts[1]
                environment[key] = value
        return environment

    def load_per_item_environment(self, section_name: str, item_name: str) -> None:
        if section_name not in self.per_item_environ or item_name not in self.per_item_environ[section_name]:
            filename = self.config.get_section_item(section_name, item_name).get('env_file', None)
            if section_name not in self.per_item_environ:
                self.per_item_environ[section_name] = {}
            if item_name not in self.per_item_environ[section_name]:
                self.per_item_environ[section_name][item_name] = {}
            self.per_item_environ[section_name][item_name] = self._load_env_file(filename)

    def replace(self, obj: Any, key: Union[str, int], value: Any, section_name: str, item_name: str) -> None:
        self.load_per_item_environment(section_name, item_name)
        replacers = self.get_deployfish_replacements(section_name, item_name)
        # FIXME: need to deal with multiple matches in the same line
        m = self.ENVIRONMENT_RE.search(value)
        if m:
            envkey = m.group('key')
            for replace_str, replace_value in list(replacers.items()):
                envkey = envkey.replace(replace_str, replace_value)
            envkey = envkey.upper().replace('-', '_')
            try:
                env_value = self.per_item_environ[section_name][item_name][envkey]
            except KeyError:
                try:
                    env_value = self.environ[envkey]
                except KeyError:
                    if not self.context.get('ignore_missing_environment', False):
                        raise self.ProcessingFailed(
                            'Config["{}"]["{}"]: Could not find value for ${{env.{}}}'.format(
                                section_name,
                                item_name,
                                envkey
                            )
                        )
                    env_value = 'NOT-IN-ENVIRONMENT'
            obj[key] = value.replace(m.group(0), env_value)
