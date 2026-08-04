import getpass
import logging
import os
import pwd
from pathlib import Path

from deployfish.core.models.ecs import Service

# pylint: disable=no-name-in-module
from deployfish.core.utils.mixins import (
    CodeNameVersionMixin,
    GitChangelogMixin,
    GitMixin,
)
from slackfin import (
    SlackFormatter,
    SlackLabelValueListBlock,
    SlackLabelValuePair,
    SlackMarkdownType,
    SlackMessage,
    SlackMessageContext,
    SlackMessageDivider,
    SlackMessageHeader,
    SlackMessageMarkdown,
)

logging.basicConfig(level=logging.WARNING)


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
    config_file = app.pargs.deployfish_filename
    repo_folder = str(Path(config_file).parent)
    channel = app.config.get("plugin.slack", "channel")
    if not channel or channel == "<user>":
        channel = f"@{getpass.getuser()}"
    _ = ServiceUpdateMessage(app, obj, repo_folder).send(channel=channel)


class DeployfishMessage(SlackMessage):
    """
    A message from deployfish.

    Args:
        app: app.
        *args: args.

    """

    def __init__(self, app, *args, **kwargs):
        """
        Initialize DeployfishMessage.

        Args:
            app: app.
            *args: args.

        Keyword Args:
            kwargs: kwargs.

        """
        token = app.config.get("plugin.slack", "token")
        super().__init__(
            SlackMessageDivider(),
            *args,
            token=token,
            **kwargs,
        )

    def add_context(self):
        """
        Add context.
        """
        self.add_block(
            SlackMessageContext(
                SlackMarkdownType(SlackFormatter().datetime()),
                SlackMarkdownType("Deployfish"),
            )
        )


class ServiceUpdateMessage(
    GitChangelogMixin, GitMixin, CodeNameVersionMixin, DeployfishMessage
):
    """
    A message indicating that a service has been updated.

    Args:
        app: app.
        obj: obj.
        repo_folder: repo folder.

    """

    def __init__(self, app, obj, repo_folder):
        """
        Initialize ServiceUpdateMessage.

        Args:
            app: app.
            obj: obj.
            repo_folder: repo folder.

        """
        if repo_folder:
            cwd = str(Path.cwd())
            os.chdir(repo_folder)
        super().__init__(
            app,
            SlackMessageHeader(text="Service Update Succeeded"),
            text="The service has been updated.",
        )
        #: Values.
        self.values = {}
        self.annotate(self.values)
        if repo_folder:
            os.chdir(cwd)

        self.add_service_update(obj)
        self.add_changelog()
        self.add_context()

    def add_service_update(self, obj):
        """
        Add service update.

        Args:
            obj: obj.

        """
        environment = obj.tags["Environment"]
        username = getpass.getuser()
        full_name = pwd.getpwnam(username).pw_gecos.split(",")[0]
        block = SlackLabelValueListBlock()
        block.add_entry(
            SlackLabelValuePair(
                label=self.values["name"],
                value="service updated",
                label_url=self.url_patterns["repo"],
            )
        )
        block.add_entry(
            SlackLabelValuePair(
                label="Environment",
                value=environment,
            )
        )
        # block.add_entry(
        #     SlackLabelValuePair(
        block.add_entry(
            SlackLabelValuePair(
                label="Committer",
                value=self.values["committer"],
            )
        )
        block.add_entry(
            SlackLabelValuePair(
                label="Authors",
                value=",".join(self.values["authors"]),
            )
        )
        block.add_entry(
            SlackLabelValuePair(
                label="Deployer",
                value=full_name,
            )
        )
        self.add_block(block)

    def add_changelog(self):
        """
        Add changelog.
        """
        changelog = self.values.get("changelog", [])
        url = "https://ads-utils-icons.s3.us-west-2.amazonaws.com/ads_dev_ops/database-check.png"
        text = "*Changelog:*\n"
        text += str.join("\n", changelog)
        if text:
            self.add_block(
                SlackMessageMarkdown(
                    text=text,
                    image_url=url,
                    alt_text="Changelog",
                )
            )
