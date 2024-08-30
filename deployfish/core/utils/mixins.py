import datetime
from distutils.core import run_setup
import os
import pathlib
import time
from typing import Dict

import docker
from git import Repo
from giturlparse import parse


class AnnotationMixin:

    def annotate(self, values: Dict[str, str]):
        pass


class PythonMixin(AnnotationMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def annotate(self, values: Dict[str, str]):
        """
        Extract some stuff from setup.py, if present.

        If setup.py is present, we'll add the following keys to `values`:

        * `name`: the output of `python setup.py name`
        * `version`: the output of `python setup.py version`

        """
        super().annotate(values)
        setup_py = pathlib.Path.cwd() / 'setup.py'
        if setup_py.exists():
            # Extract some stuff from python itself
            python_setup = run_setup(str(setup_py))
            values['name'] = python_setup.get_name()
            values['version'] = python_setup.get_version()


class GitMixin(AnnotationMixin):

    def __init__(self, *args, url_type="slack", **kwargs):
        self.repo = None
        self.url_type = url_type
        self.url_patterns = {}
        self.__get_repo()
        self.__build_url_patterns()
        super().__init__(*args, **kwargs)

    def __get_repo(self):
        if not self.repo:
            self.repo = Repo('.')

    def __format_url(self, url: str, label: str):
        if self.url_type == "markdown":
            return f"[{label}]({url})"
        return f"<{url}|{label}>"

    def __build_url_patterns(self):
        # https://caltech-imss-ads@bitbucket.org/caltech-imss-ads/exeter_api/src/0.10.2/
        #
        if not self.url_patterns:
            p = parse(self.repo.remote().url)
            origin_url = f"https://{p.host}/{p.owner}/{p.repo}"
            if origin_url.endswith('.git'):
                origin_url = origin_url[:-4]
            if p.bitbucket:
                self.url_patterns['commit'] = self.__format_url(url=f"{origin_url}/commits/" + "{sha}", label="{sha}")
                self.url_patterns['project'] = self.__format_url(url=f"{origin_url}/src/" + "{version}/", label="{name}")
                self.url_patterns['diff'] = self.__format_url(url=f"{origin_url}/branches/compare/" + "{from_sha}..{to_sha}#diff", label="{from_sha}..{to_sha}")
            elif p.github:
                self.url_patterns['commit'] = self.__format_url(url=f"{origin_url}/commit/" + "{sha}", label="{sha}")
                self.url_patterns['project'] = self.__format_url(url=f"{origin_url}/tree/" + "{version}", label="{name}")
                self.url_patterns['diff'] = self.__format_url(url=f"{origin_url}/compare/" + "{from_sha}..{to_sha}", label="{from_sha}..{to_sha}")
            else:
                self.url_patterns['commit'] = "{sha}"
                self.url_patterns['project'] = "{name}"
                self.url_patterns['diff'] = None
            self.url_patterns['repo'] = origin_url

    def __get_last_version(self, values: Dict[str, str]):
        """
        Update the `values` dict with:

        * `previous_version`: the version number for the tag immediately preceeding ours
        * `last_version_sha`: the sha that that tag points to
        """
        # Get all tags, sorted by the authored_date on their associated commit.  We should have at least one tag -- the
        # one for this commit.
        ordered_tags = sorted(self.repo.tags, key=lambda x: x.commit.authored_date)
        if len(ordered_tags) >= 2:
            # If there are 2 or more tags, there was a previous version.
            # Extract info from the tag preceeding this one.
            values['last_version_sha'] = ordered_tags[-2].commit.hexsha
            values['last_version_url'] = self.url_patterns['project'].format(
                version=values['version'],
                name=f"{values['name']}-{values['version']}"
            )
            values['previous_version'] = ordered_tags[-2].name
        else:
            # There was just our current version tag, and no previous tag.  Go back to the initial commit.
            commits = list(self.repo.iter_commits())
            commits.reverse()
            values['last_version_sha'] = commits[0].hexsha
            values['last_version_url'] = self.url_patterns['project'].format(
                version=values['version'],
                name=f"{values['name']}-{values['version']}"
            )
            values['previous_version'] = "initial"

    def git_changelog(self, values: Dict[str, str]):
        """
        Look through the commits between the current version and the last version
        Update `values` with two new keys:

        * `authors`: a list of all authors in those commits
        * `changelog`: a list of strings representing the commits
        """
        # get the changes between here and the previous tag
        changelog_commits = []
        current = self.repo.head.commit
        # Gather all commits from HEAD to `last_version_sha`
        while True:
            changelog_commits.append(current)
            if current.hexsha == values['last_version_sha']:
                break
            current = current.parents[0]
        changelog = []
        authors = set()
        for commit in changelog_commits:
            authors.add(commit.author.name)
            d = datetime.datetime.fromtimestamp(commit.committed_date).strftime("%Y/%m/%d")
            commit_link = self.url_patterns['commit'].format(sha=commit.hexsha[0:7])
            changelog.append(f"{commit_link} [{d}] {commit.summary} - {str(commit.author)}")
        values['authors'] = sorted(authors)
        values['changelog'] = changelog

    def __get_concise_info(self):
        branch = self.repo.head.reference.name
        current = self.repo.head.commit
        sha = current.hexsha[0:7]
        sha_url = self.url_patterns['commit'].format(sha=sha)
        committer = f"{current.author.name} <{current.author.email}>"
        return f"{branch} {sha_url} {committer}"

    def annotate(self, values: Dict[str, str]):
        """
        Extract info about the git repo.  Assume we're in the checked out clone.
        """
        super().annotate(values)
        headcommit = self.repo.head.commit
        values['committer'] = str(headcommit.author)
        values['sha'] = headcommit.hexsha
        values['branch'] = self.repo.head.reference.name
        self.__get_last_version(values)
        # Add the diff URL
        if 'diff' in self.url_patterns:
            values['diff_url'] = self.url_patterns['diff'].format(
                from_sha=values['sha'][0:7],
                to_sha=values['last_version_sha'][0:7],
            )
        values['git_info'] = self.__get_concise_info()


class GitChangelogMixin:
    """
    This needs to be used after GitMixin in the inheritance chain.
    """

    def annotate(self, values: Dict[str, str]):
        """
        Look through the commits between the current version and the last version
        Update `values` with two new keys:

        * `authors`: a list of all authors in those commits
        * `changelog`: a list of strings representing the commits
        """
        super().annotate(values)
        # get the changes between here and the previous tag
        changelog_commits = []
        current = self.repo.head.commit
        # Gather all commits from HEAD to `last_version_sha`
        while True:
            changelog_commits.append(current)
            if current.hexsha == values['last_version_sha']:
                break
            current = current.parents[0]
        changelog = []
        authors = set()
        for commit in changelog_commits:
            authors.add(commit.author.name)
            d = datetime.datetime.fromtimestamp(commit.committed_date).strftime("%Y/%m/%d")
            commit_link = self.url_patterns['commit'].format(sha=commit.hexsha[0:7])
            changelog.append(f"{commit_link} [{d}] {commit.summary} - {str(commit.author)}")
        values['authors'] = sorted(authors)
        values['changelog'] = changelog


class CodebuildMixin(AnnotationMixin):

    def __init__(self, *args, **kwargs):
        if 'log_group' in kwargs:
            self.log_group = kwargs['log_group']
        super().__init__(*args, **kwargs)

    def annotate(self, values: Dict[str, str]):
        super().annotate(values)
        values['status'] = 'Success' if 'CODEBUILD_BUILD_SUCCEEDING' in os.environ else 'Failed'
        values['region'] = os.environ['AWS_DEFAULT_REGION']
        values['build_id'] = os.environ.get('CODEBUILD_BUILD_ID', None)
        build_seconds = time.time() - float(os.environ['CODEBUILD_START_TIME'])
        build_minutes = int(build_seconds // 60)
        build_seconds = int(build_seconds - build_minutes * 60)
        values['build_time'] = f"{build_minutes}m {build_seconds}s"
        values['build_status_url'] = f"<https://{values['region']}.console.aws.amazon.com/codebuild/home/?region={values['region']}/builds/{values['build_id']}|Click here>"  # noqa:E501


class DockerImageNameMixin(AnnotationMixin):

    def __init__(self, *args, **kwargs):
        if 'image' in kwargs:
            self.image = kwargs['image']
            del kwargs['image']
        super().__init__(*args, **kwargs)

    def annotate(self, values):
        super().annotate(values)
        values['short_image'] = os.path.basename(self.image)


class DockerMixin(AnnotationMixin):

    def __init__(self, *args, **kwargs):
        if 'image' in kwargs:
            self.image = kwargs['image']
            del kwargs['image']
        super().__init__(*args, **kwargs)

    def annotate(self, values: Dict[str, str]):
        super().annotate(values)
        client = docker.from_env()
        image = client.images.get(self.image)
        values['image_id'] = image.short_id.split(':')[1]
        values['image_size'] = image.attrs['Size'] / (1024 * 1024)


class DeployfishDeployMixin(AnnotationMixin):

    def __init__(self, *args, **kwargs):
        if 'service' in kwargs:
            self.service = kwargs['service']
            del kwargs['service']
        super().__init__(*args, **kwargs)

    def annotate(self, values: Dict[str, str]):
        super().annotate(values)
        values['service'] = self.service
