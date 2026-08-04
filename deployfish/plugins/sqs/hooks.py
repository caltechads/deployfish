import configparser
import datetime
import getpass
import logging
import os
import pwd
from pathlib import Path

import click
from deployfish.core.models.ecs import Service

# pylint: disable=no-name-in-module
from deployfish.core.utils.mixins import (
    CodeNameVersionMixin,
    GitChangelogMixin,
    GitMixin,
)
from simplesqs.message import MessagingHandler
from tzlocal import get_localzone

logging.basicConfig(level=logging.WARNING)


class Annotator(GitChangelogMixin, GitMixin, CodeNameVersionMixin):
    """
    Annotate a service update with a git changelog.

    Args:
        app: app.
        obj: obj.
        repo_folder: repo folder.

    """

    def __init__(self, app, obj, repo_folder):
        #: App.
        """
        Initialize Annotator.

        Args:
            app: app.
            obj: obj.
            repo_folder: repo folder.

        """
        #: App.
        self.app = app
        #: Obj.
        self.obj = obj
        #: Repo folder.
        self.repo_folder = repo_folder
        if repo_folder:
            cwd = str(Path.cwd())
            os.chdir(repo_folder)
        super().__init__(url_type="markdown")
        #: Values.
        self.values = {}
        self.annotate(self.values)
        if repo_folder:
            os.chdir(cwd)
        username = getpass.getuser()
        full_name = pwd.getpwnam(username).pw_gecos.split(",")[0]
        self.values["deployer"] = full_name

    def get_repo_url(self):
        """
        Get the repo for a service.

        Returns:
            Operation result.

        """
        return self.url_patterns["repo"]

    def get_changelog(self):
        """
        Get the changelog for a repo.

        Returns:
            Operation result.

        """
        return self.values.get("changelog", [])

    def get_environment(self):
        """
        Get the environment for a service.

        Returns:
            Operation result.

        """
        return self.obj.tags["Environment"]

    def get_authors(self):
        """
        Get the authors for the most recent commits.

        Returns:
            Operation result.

        """
        return self.values.get("authors", [])

    def get_author_string(self):
        """
        Get the authors for the most recent commits.

        Returns:
            Operation result.

        """
        authors = self.get_authors()
        return ", ".join(authors)

    def get_committer(self):
        """
        Get the committer for the most recent commits.

        Returns:
            Operation result.

        """
        return self.values.get("committer", "")

    def get_deployer(self):
        """
        Get the deployer for the most recent commits.

        Returns:
            Operation result.

        """
        return self.values.get("deployer", "")

    def get_version(self):
        """
        Get the version for the most recent commits.

        Returns:
            Operation result.

        """
        return self.values.get("version", "initial")

    def get_repo_name(self):
        """
        Get the name of the service.

        Returns:
            Operation result.

        """
        return self.values.get("name", "")

    def get_service_name(self):
        """
        Get the name of the service.

        Returns:
            Operation result.

        """
        name_env = self.obj.data["serviceName"]
        dash = name_env.rfind("-")
        return name_env[:dash]

    def get_title(self):
        """
        Get the title for the message.

        Returns:
            Operation result.

        """
        return f"{self.get_service_name()} {self.get_version()}"

    def get_deploy_timestamp(self):
        """
        Get the deploy datetime for the message.

        Returns:
            Operation result.

        """
        local_tz = get_localzone()
        current_time = datetime.datetime.now(local_tz)
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S.%f%z")
        return formatted_time[:-2] + ":" + formatted_time[-2:]

    def get_description(self):
        """
        Get the description for the message.

        Returns:
            Operation result.

        """
        description = ""
        description += f"**Deployer**: {self.get_deployer()}\n"
        description += "\n"
        description += "**Changelog**\n\n"
        for log in self.get_changelog():
            if "Bump version" not in log:
                description += f"* {log}\n"
        return description


def process_service_update(app, obj, success=True, reason=None):  # noqa: ARG001, FBT002
    """
    Process service update.

    Args:
        app: app.
        obj: obj.
        success: success.
        reason: reason.

    """
    if not success:
        return
    if not isinstance(obj, Service):
        return
    try:
        queues = app.config.get("plugin.sqs", "queues")
    except configparser.NoOptionError:
        app.print(click.style("No SQS queues defined in `/.deployfish.yml", fg="red"))
        return
    config_file = app.pargs.deployfish_filename
    repo_folder = str(Path(config_file).parent)
    annotator = Annotator(app, obj, repo_folder)
    message = {
        "service": annotator.get_repo_name(),
        "title": annotator.get_title(),
        "environment": annotator.get_environment(),
        "description": annotator.get_description(),
        "timestamp": annotator.get_deploy_timestamp(),
    }
    for queue in queues:
        queue_name = queue["name"]
        queue_type = queue["type"]
        queue_profile = queue.get("profile", None)
        response = MessagingHandler(
            queue_name=queue_name, aws_profile=queue_profile
        ).send_message(queue_type, message)
        app.print(
            click.style(f"Message submitted. ID: {response['MessageId']}.", fg="green")
        )
