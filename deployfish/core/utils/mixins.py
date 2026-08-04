import datetime
import os
import pathlib
import subprocess
import time
from pathlib import Path
from typing import Any, cast

import docker
import toml
from git import Repo
from giturlparse import parse


class ImproperlyConfiguredError(Exception):
    """
    We programmers improperly configured something.
    """


class AnnotationMixin:
    """
    Model annotation mixin behavior.
    """

    def annotate(self, context: dict[str, str]):
        """
        Annotate.

        Args:
            context: context.

        """


class CodeNameVersionMixin(AnnotationMixin):
    """
    Model code name version mixin behavior.
    """

    def setup_py(self, path: pathlib.Path) -> dict[str, str]:
        """
        Process a setup.py file and return the name and version.

        Raises:
            ValueError: if the setup.py is a stub, and doesn't
                contain a version and name

        Args:
            path: the path to the setup.py file

        Returns:
            A dictionary with the keys ``name`` and ``version``

        """
        context: dict[str, str] = {}
        context["version"] = subprocess.run(
            ["/usr/bin/env", "python", str(path), "--version"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if context["version"] == "0.0.0":
            msg = "setup.py is a stub"
            raise ValueError(msg)
        context["name"] = subprocess.run(
            ["/usr/bin/env", "python", str(path), "--name"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return context

    def makefile(self, path: pathlib.Path) -> dict[str, str]:
        """
        Process a Makefile and return the name and version.

        Raises:
            ValueError: if the Makefile doesn't contain the
                ``image_name`` or ``version`` targets

        Args:
            path: the path to the Makefile

        Returns:
            A dictionary with the keys ``name`` and ``version``

        """
        context: dict[str, str] = {}
        # This command line extracts the names of the targets from the Makefile,
        # ignoring the implicit ones, and sorts them.
        command = ["make", "-pRrq", "-f", str(path)]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.CalledProcessError:  # noqa: TRY203
            raise
        if "image_name:" not in result.stdout:
            msg = "Makefile does not contain an image_name target"
            raise ValueError(msg)
        if "version:" not in result.stdout:
            msg = "Makefile does not contain a version target"
            raise ValueError(msg)
        context["name"] = (
            subprocess.check_output(["make", "image_name"]).decode("utf8").strip()
        )
        context["version"] = (
            subprocess.check_output(["make", "version"]).decode("utf8").strip()
        )
        return context

    def pyproject_toml(self, path: pathlib.Path) -> dict[str, str]:
        """
        Process a pyproject.toml file and return the name and version.

        Raises:
            ValueError: if the pyproject.toml is a stub, and doesn't
                contain a version and name

        Args:
            path: the path to the pyproject.toml file

        Returns:
            A dictionary with the keys ``name`` and ``version``

        """
        context: dict[str, str] = {}
        data = toml.load(path)
        if "project" not in data:
            msg = "pyproject.toml is a stub: no project section"
            raise ValueError(msg)
        context["name"] = data["project"]["name"]
        context["version"] = data["project"]["version"]
        return context

    def annotate(self, context: dict[str, str]):
        """
        Extract some stuff from setup.py, if present.

        If setup.py is present, we'll add the following keys to `values`:

        * `name`: the output of `python setup.py name`
        * `version`: the output of `python setup.py version`

        Args:
            context: context.

        """
        super().annotate(context)
        setup_py = pathlib.Path.cwd() / "setup.py"
        makefile = pathlib.Path.cwd() / "Makefile"
        pyproject_toml = pathlib.Path.cwd() / "pyproject.toml"
        if setup_py.exists():
            try:
                context.update(self.setup_py(setup_py))
            except ValueError:
                pass
            else:
                return
        if pyproject_toml.exists():
            try:
                context.update(self.pyproject_toml(pyproject_toml))
            except ValueError:
                pass
            else:
                return
        if makefile.exists():
            try:
                context.update(self.makefile(makefile))
            except ValueError:
                pass
            else:
                return
        msg = "Cannot determine project name and version"
        raise ImproperlyConfiguredError(msg)


class GitMixin(AnnotationMixin):
    """
    Model git mixin behavior.

    Args:
        *args: args.

    """

    def __init__(self, *args, url_type="slack", **kwargs):
        #: Repo.
        """
        Initialize GitMixin.

        Args:
            *args: args.

        Keyword Args:
            url_type: url type.
            kwargs: kwargs.

        """
        #: Repo.
        self.repo = None
        #: Url type.
        self.url_type = url_type
        #: Url patterns.
        self.url_patterns = {}
        self.__get_repo()
        self.__build_url_patterns()
        super().__init__(*args, **kwargs)

    def __get_repo(self):
        """
        Handle get repo.
        """
        if not self.repo:
            self.repo = Repo(".")

    def __format_url(self, url: str, label: str):
        """
        Handle format url.

        Args:
            url: url.
            label: label.

        Returns:
            Operation result.

        """
        if self.url_type == "markdown":
            return f"[{label}]({url})"
        return f"<{url}|{label}>"

    def __build_url_patterns(self):
        # https://caltech-imss-ads@bitbucket.org/caltech-imss-ads/exeter_api/src/0.10.2/
        #
        """
        Handle build url patterns.
        """
        if not self.url_patterns:
            p = parse(self.repo.remote().url)
            origin_url = f"https://{p.host}/{p.owner}/{p.repo}"
            origin_url = origin_url.removesuffix(".git")
            if p.bitbucket:
                self.url_patterns["commit"] = self.__format_url(
                    url=f"{origin_url}/commits/" + "{sha}", label="{sha}"
                )
                self.url_patterns["project"] = self.__format_url(
                    url=f"{origin_url}/src/" + "{version}/", label="{name}"
                )
                self.url_patterns["diff"] = self.__format_url(
                    url=f"{origin_url}/branches/compare/{{from_sha}}..{{to_sha}}#diff",
                    label="{from_sha}..{to_sha}",
                )
            elif p.github:
                self.url_patterns["commit"] = self.__format_url(
                    url=f"{origin_url}/commit/" + "{sha}", label="{sha}"
                )
                self.url_patterns["project"] = self.__format_url(
                    url=f"{origin_url}/tree/" + "{version}", label="{name}"
                )
                self.url_patterns["diff"] = self.__format_url(
                    url=f"{origin_url}/compare/" + "{from_sha}..{to_sha}",
                    label="{from_sha}..{to_sha}",
                )
            else:
                self.url_patterns["commit"] = "{sha}"
                self.url_patterns["project"] = "{name}"
                self.url_patterns["diff"] = None
            self.url_patterns["repo"] = origin_url

    def __get_last_version(self, values: dict[str, str]):
        """
        Update the `values` dict with:

        * `previous_version`: the version number for the tag immediately preceeding ours
        * `last_version_sha`: the sha that that tag points to

        Args:
            values: values.

        """
        # Get all tags, sorted by the authored_date on their associated commit.  We should have at least one tag -- the  # noqa: E501
        # one for this commit.
        ordered_tags = sorted(self.repo.tags, key=lambda x: x.commit.authored_date)
        if len(ordered_tags) >= 2:  # noqa: PLR2004
            # If there are 2 or more tags, there was a previous version.
            # Extract info from the tag preceeding this one.
            values["last_version_sha"] = ordered_tags[-2].commit.hexsha
            values["last_version_url"] = self.url_patterns["project"].format(
                version=values["version"],
                name=f"{values['name']}-{values['version']}",
            )
            values["previous_version"] = ordered_tags[-2].name
        else:
            # There was just our current version tag, and no previous tag.  Go back to the initial commit.  # noqa: E501
            commits = list(self.repo.iter_commits())
            commits.reverse()
            values["last_version_sha"] = commits[0].hexsha
            values["last_version_url"] = self.url_patterns["project"].format(
                version=values["version"],
                name=f"{values['name']}-{values['version']}",
            )
            values["previous_version"] = "initial"

    def git_changelog(self, values: dict[str, Any]) -> None:
        """
        Look through the commits between the current version and the last version
        Update `values` with two new keys:

        * `authors`: a list of all authors in those commits
        * `changelog`: a list of strings representing the commits

        Args:
            values: values.

        """
        # get the changes between here and the previous tag
        changelog_commits = []
        current = self.repo.head.commit
        # Gather all commits from HEAD to `last_version_sha`
        while True:
            changelog_commits.append(current)
            if current.hexsha == values["last_version_sha"]:
                break
            current = current.parents[0]
        changelog = []
        authors = set()
        for commit in changelog_commits:
            authors.add(commit.author.name)
            d = datetime.datetime.fromtimestamp(
                commit.committed_date, tz=datetime.UTC
            ).strftime(
                "%Y/%m/%d"
            )
            commit_link = self.url_patterns["commit"].format(sha=commit.hexsha[0:7])
            changelog.append(
                f"{commit_link} [{d}] {commit.summary} - {commit.author!s}"
            )
        values["authors"] = sorted(authors)
        values["changelog"] = changelog

    def __get_concise_info(self):
        """
        Handle get concise info.

        Returns:
            Operation result.

        """
        branch = self.repo.head.reference.name
        current = self.repo.head.commit
        sha = current.hexsha[0:7]
        sha_url = self.url_patterns["commit"].format(sha=sha)
        committer = f"{current.author.name} <{current.author.email}>"
        return f"{branch} {sha_url} {committer}"

    def annotate(self, values: dict[str, str]):
        """
        Extract info about the git repo.  Assume we're in the checked out clone.

        Args:
            values: values.

        """
        super().annotate(values)
        headcommit = self.repo.head.commit
        values["committer"] = str(headcommit.author)
        values["sha"] = headcommit.hexsha
        values["branch"] = self.repo.head.reference.name
        self.__get_last_version(values)
        # Add the diff URL
        if "diff" in self.url_patterns:
            values["diff_url"] = self.url_patterns["diff"].format(
                from_sha=values["sha"][0:7],
                to_sha=values["last_version_sha"][0:7],
            )
        values["git_info"] = self.__get_concise_info()


class GitChangelogMixin:
    """

    needs to be used after GitMixin in the inheritance chain.
    """

    def annotate(self, values: dict[str, Any]) -> None:
        """
        Look through the commits between the current version and the last version
        Update `values` with two new keys:

        * `authors`: a list of all authors in those commits
        * `changelog`: a list of strings representing the commits

        Args:
            values: values.

        """
        super().annotate(values)  # type: ignore[misc]
        git_mixin = cast("GitMixin", self)
        # get the changes between here and the previous tag
        changelog_commits = []
        current = git_mixin.repo.head.commit
        # Gather all commits from HEAD to `last_version_sha`
        while True:
            changelog_commits.append(current)
            if current.hexsha == values["last_version_sha"]:
                break
            current = current.parents[0]
        changelog = []
        authors = set()
        for commit in changelog_commits:
            authors.add(commit.author.name)
            d = datetime.datetime.fromtimestamp(
                commit.committed_date, tz=datetime.UTC
            ).strftime(
                "%Y/%m/%d"
            )
            commit_link = git_mixin.url_patterns["commit"].format(
                sha=commit.hexsha[0:7]
            )
            changelog.append(
                f"{commit_link} [{d}] {commit.summary} - {commit.author!s}"
            )
        values["authors"] = sorted(authors)
        values["changelog"] = changelog


class CodebuildMixin(AnnotationMixin):
    """
    Model codebuild mixin behavior.

    Args:
        *args: args.

    """

    def __init__(self, *args, **kwargs):
        """
        Initialize CodebuildMixin.

        Args:
            *args: args.

        Keyword Args:
            kwargs: kwargs.

        """
        if "log_group" in kwargs:
            #: Log group.
            self.log_group = kwargs["log_group"]
        super().__init__(*args, **kwargs)

    def annotate(self, values: dict[str, Any]) -> None:
        """
        Annotate.

        Args:
            values: values.

        """
        super().annotate(values)
        values["status"] = (
            "Success" if "CODEBUILD_BUILD_SUCCEEDING" in os.environ else "Failed"
        )
        values["region"] = os.environ["AWS_DEFAULT_REGION"]
        values["build_id"] = os.environ.get("CODEBUILD_BUILD_ID", "")
        build_seconds = time.time() - float(os.environ["CODEBUILD_START_TIME"])
        build_minutes = int(build_seconds // 60)
        build_seconds = int(build_seconds - build_minutes * 60)
        values["build_time"] = f"{build_minutes}m {build_seconds}s"
        values["build_status_url"] = (
            f"<https://{values['region']}.console.aws.amazon.com/codebuild/home/?region={values['region']}/builds/{values['build_id']}|Click here>"  # noqa:E501
        )


class DockerImageNameMixin(AnnotationMixin):
    """
    Model docker image name mixin behavior.

    Args:
        *args: args.

    """

    def __init__(self, *args, **kwargs):
        """
        Initialize DockerImageNameMixin.

        Args:
            *args: args.

        Keyword Args:
            kwargs: kwargs.

        """
        if "image" in kwargs:
            #: Image.
            self.image = kwargs["image"]
            del kwargs["image"]
        super().__init__(*args, **kwargs)

    def annotate(self, values):
        """
        Annotate.

        Args:
            values: values.

        """
        super().annotate(values)
        values["short_image"] = Path(self.image).name


class DockerMixin(AnnotationMixin):
    """
    Model docker mixin behavior.

    Args:
        *args: args.

    """

    def __init__(self, *args, **kwargs):
        """
        Initialize DockerMixin.

        Args:
            *args: args.

        Keyword Args:
            kwargs: kwargs.

        """
        if "image" in kwargs:
            #: Image.
            self.image = kwargs["image"]
            del kwargs["image"]
        super().__init__(*args, **kwargs)

    def annotate(self, values: dict[str, str]):
        """
        Annotate.

        Args:
            values: values.

        """
        super().annotate(values)
        client = docker.from_env()
        image = client.images.get(self.image)
        values["image_id"] = image.short_id.split(":")[1]
        values["image_size"] = image.attrs["Size"] / (1024 * 1024)


class DeployfishDeployMixin(AnnotationMixin):
    """
    Model deployfish deploy mixin behavior.

    Args:
        *args: args.

    """

    def __init__(self, *args, **kwargs):
        """
        Initialize DeployfishDeployMixin.

        Args:
            *args: args.

        Keyword Args:
            kwargs: kwargs.

        """
        if "service" in kwargs:
            #: Service.
            self.service = kwargs["service"]
            del kwargs["service"]
        super().__init__(*args, **kwargs)

    def annotate(self, values: dict[str, str]):
        """
        Annotate.

        Args:
            values: values.

        """
        super().annotate(values)
        values["service"] = self.service
