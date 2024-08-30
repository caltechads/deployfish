import logging
import os
import getpass
import pwd

from slackfin import (
    SlackFormatter,
    SlackLabelValueListBlock,
    SlackLabelValuePair,
    SlackMarkdownType,
    SlackMessageContext,
    SlackMessageDivider,
    SlackMessageHeader,
    SlackMessage,
    SlackMessageMarkdown,
)

#pylint: disable=no-name-in-module
from deployfish.core.utils.mixins import (
    PythonMixin,
    GitMixin,
    GitChangelogMixin,
)

from deployfish.core.models.ecs import Service

logging.basicConfig(level=logging.WARNING)


def process_service_update(app, obj, success=True, reason=None):
    if not success:
        return
    if not isinstance(obj, Service):
        return
    config_file = app.pargs.deployfish_filename
    repo_folder = os.path.dirname(config_file)
    channel = app.config.get("plugin.slack", "channel")
    if not channel or channel == "<user>":
        channel = f"@{getpass.getuser()}"
    _ = ServiceUpdateMessage(app, obj, repo_folder).send(channel=channel)

class DeployfishMessage(SlackMessage):
    """A message from deployfish."""

    def __init__(self, app, *args, **kwargs):
        token = app.config.get("plugin.slack", "token")
        super().__init__(
            SlackMessageDivider(),
            *args,
            token=token,
            **kwargs,
        )

    def add_context(self):
        self.add_block(
            SlackMessageContext(
                SlackMarkdownType(SlackFormatter().datetime()),
                SlackMarkdownType("Deployfish"),
            )
        )


class ServiceUpdateMessage(GitChangelogMixin, GitMixin, PythonMixin, DeployfishMessage):
    """A message indicating that a service has been updated."""

    def __init__(self, app, obj, repo_folder):
        if repo_folder:
            cwd = os.getcwd()
            os.chdir(repo_folder)
        super().__init__(
            app,
            SlackMessageHeader(text="Service Update Succeeded"),
            text="The service has been updated.",
        )
        self.values = {}
        self.annotate(self.values)
        if repo_folder:
            os.chdir(cwd)

        self.add_service_update(obj)
        self.add_changelog()
        self.add_context()

    def add_service_update(self, obj):
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
        #         label="Cluster",
        #         value=obj.cluster.pk,
        #     )
        # )
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
