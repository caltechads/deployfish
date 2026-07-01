import pathlib
from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.utils.mixins import (
    CodeNameVersionMixin,
    GitMixin,
    ImproperlyConfiguredError,
)


class TestCodeNameVersionMixin:
    def test_pyproject_toml_reads_name_and_version(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = tmp_path / "pyproject.toml"
        path.write_text(
            '[project]\nname = "myapp"\nversion = "1.2.3"\n',
            encoding="utf-8",
        )
        mixin = CodeNameVersionMixin()
        context = mixin.pyproject_toml(path)
        assert context == {"name": "myapp", "version": "1.2.3"}

    def test_pyproject_toml_stub_raises(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "pyproject.toml"
        path.write_text("[tool.ruff]\nline-length = 88\n", encoding="utf-8")
        mixin = CodeNameVersionMixin()
        with pytest.raises(ValueError, match="stub"):
            mixin.pyproject_toml(path)

    def test_setup_py_reads_name_and_version(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "setup.py"
        path.write_text("# setup\n", encoding="utf-8")
        mixin = CodeNameVersionMixin()
        version_result = MagicMock(stdout="2.0.0\n")
        name_result = MagicMock(stdout="deployfish\n")
        with patch(
            "deployfish.core.utils.mixins.subprocess.run",
            side_effect=[version_result, name_result],
        ):
            context = mixin.setup_py(path)
        assert context == {"name": "deployfish", "version": "2.0.0"}

    def test_setup_py_stub_raises(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "setup.py"
        mixin = CodeNameVersionMixin()
        stub_result = MagicMock(stdout="0.0.0\n")
        with patch(
            "deployfish.core.utils.mixins.subprocess.run", return_value=stub_result
        ), pytest.raises(ValueError, match="stub"):
            mixin.setup_py(path)

    def test_makefile_reads_targets(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "Makefile"
        path.write_text(
            "image_name:\n\t@echo app\nversion:\n\t@echo 3.0.0\n", encoding="utf-8"
        )
        mixin = CodeNameVersionMixin()
        list_result = MagicMock(stdout="image_name:\nversion:\n", stderr="")
        with patch(
            "deployfish.core.utils.mixins.subprocess.run", return_value=list_result
        ), patch(
            "deployfish.core.utils.mixins.subprocess.check_output",
            side_effect=[b"app\n", b"3.0.0\n"],
        ):
            context = mixin.makefile(path)
        assert context == {"name": "app", "version": "3.0.0"}

    def test_annotate_uses_pyproject_toml(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "svc"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        mixin = CodeNameVersionMixin()
        context: dict[str, str] = {}
        mixin.annotate(context)
        assert context == {"name": "svc", "version": "0.1.0"}

    def test_annotate_raises_when_no_metadata(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        mixin = CodeNameVersionMixin()
        with pytest.raises(ImproperlyConfiguredError):
            mixin.annotate({})


class TestGitMixin:
    def test_format_url_slack_style(self) -> None:
        mixin = GitMixin(url_type="slack")
        assert (
            mixin._GitMixin__format_url("https://example.com", "link")  # type: ignore[attr-defined]
            == "<https://example.com|link>"
        )

    def test_format_url_markdown_style(self) -> None:
        mixin = GitMixin(url_type="markdown")
        assert (
            mixin._GitMixin__format_url("https://example.com", "link")  # type: ignore[attr-defined]
            == "[link](https://example.com)"
        )
