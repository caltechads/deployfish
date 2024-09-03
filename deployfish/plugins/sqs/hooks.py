import configparser
import datetime
import logging
import os
import getpass
import pwd

import click
from tzlocal import get_localzone

from simplesqs.message import MessagingHandler

#pylint: disable=no-name-in-module
from deployfish.core.utils.mixins import (
    PythonMixin,
    GitMixin,
    GitChangelogMixin,
)

from deployfish.core.models.ecs import Service

logging.basicConfig(level=logging.WARNING)


class Annotator(GitChangelogMixin, GitMixin, PythonMixin):
    """Annotate a service update with a git changelog."""
    def __init__(self, app, obj, repo_folder):
        self.app = app
        self.obj = obj
        self.repo_folder = repo_folder
        if repo_folder:
            cwd = os.getcwd()
            os.chdir(repo_folder)
        super().__init__(url_type="markdown")
        self.values = {}
        self.annotate(self.values)
        if repo_folder:
            os.chdir(cwd)
        username = getpass.getuser()
        full_name = pwd.getpwnam(username).pw_gecos.split(",")[0]
        self.values["deployer"] = full_name

    def get_repo_url(self):
        """Get the repo for a service."""
        return self.url_patterns["repo"]

    def get_changelog(self):
        """Get the changelog for a repo."""
        return self.values.get("changelog", [])

    def get_environment(self):
        """Get the environment for a service."""
        environment = self.obj.tags["Environment"]
        return environment

    def get_authors(self):
        """Get the authors for the most recent commits."""
        return self.values.get("authors", [])

    def get_author_string(self):
        """Get the authors for the most recent commits."""
        authors = self.get_authors()
        author_str = ", ".join(authors)
        return author_str

    def get_committer(self):
        """Get the committer for the most recent commits."""
        return self.values.get("committer", "")

    def get_deployer(self):
        """Get the deployer for the most recent commits."""
        return self.values.get("deployer", "")

    def get_version(self):
        """Get the version for the most recent commits."""
        return self.values.get("version", "initial")

    def get_repo_name(self):
        """Get the name of the service."""
        return self.values.get("name", "")

    def get_service_name(self):
        """Get the name of the service."""
        name_env = self.obj.data['serviceName']
        dash = name_env.rfind('-')
        service_name = name_env[:dash]
        return service_name

    def get_title(self):
        """Get the title for the message."""
        return f"{self.get_service_name()} {self.get_version()}"

    def get_deploy_timestamp(self):
        """Get the deploy datetime for the message."""
        local_tz = get_localzone()
        current_time = datetime.datetime.now(local_tz)
        formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S.%f%z')
        formatted_time = formatted_time[:-2] + ':' + formatted_time[-2:]
        return formatted_time

    def get_description(self):
        """Get the description for the message."""
        description  = ""
        # description += f"**Committer**: {self.get_committer()}\n"
        # description += f"**Authors**: {self.get_author_string()}\n"
        description += f"**Deployer**: {self.get_deployer()}\n"
        description += "\n"
        description += "**Changelog**\n\n"
        for log in self.get_changelog():
            if not "Bump version" in log:
                description += f"* {log}\n"
        return description


def process_service_update(app, obj, success=True, reason=None):
    if not success:
        return
    if not isinstance(obj, Service):
        return
    try:
        queues = app.config.get("plugin.sqs", "queues")
    except configparser.NoOptionError:
        app.print(click.style("No SQS queues defined in `/.deployfish.yml", fg='red'))
        print("No SQS queues defined in `/.deployfish.yml")
        return
    config_file = app.pargs.deployfish_filename
    repo_folder = os.path.dirname(config_file)
    annotator = Annotator(app, obj, repo_folder)
    message = {
        'service': annotator.get_repo_name(),
        'title': annotator.get_title(),
        'environment': annotator.get_environment(),
        'description': annotator.get_description(),
        'timestamp': annotator.get_deploy_timestamp(),
    }
    for queue in queues:
        queue_name = queue['name']
        queue_type = queue['type']
        queue_profile = queue.get('profile', None)
        response = MessagingHandler(
            queue_name=queue_name,
            aws_profile=queue_profile
        ).send_message(queue_type, message)
        app.print(click.style(f"Message submitted. ID: {response['MessageId']}.", fg='green'))
