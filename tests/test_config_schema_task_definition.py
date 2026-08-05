"""Tests for the TaskDefinitionInput sub-models."""

import pytest
from deployfish.config.schema.task_definition import Volume
from pydantic import ValidationError


class TestVolume:
    def test_path_only(self) -> None:
        v = Volume.model_validate({"name": "host-vol", "path": "/data"})
        assert v.path == "/data"
        assert v.config is None
        assert v.efs_config is None

    def test_config_only(self) -> None:
        v = Volume.model_validate(
            {
                "name": "docker-vol",
                "config": {"scope": "task", "autoprovision": True, "driver": "local"},
            }
        )
        assert v.config is not None
        assert v.config.scope == "task"
        assert v.config.autoprovision is True
        assert v.config.driver == "local"

    def test_efs_config_only(self) -> None:
        v = Volume.model_validate(
            {
                "name": "efs-vol",
                "efs_config": {"file_system_id": "fs-123", "root_directory": "/mnt"},
            }
        )
        assert v.efs_config is not None
        assert v.efs_config.file_system_id == "fs-123"
        assert v.efs_config.root_directory == "/mnt"

    def test_efs_config_root_directory_optional(self) -> None:
        v = Volume.model_validate(
            {"name": "efs-vol", "efs_config": {"file_system_id": "fs-123"}}
        )
        assert v.efs_config is not None
        assert v.efs_config.root_directory is None

    def test_path_and_config_both_set_raises(self) -> None:
        with pytest.raises(ValidationError, match='only one of "path"'):
            Volume.model_validate(
                {"name": "bad", "path": "/a", "config": {"scope": "task"}}
            )

    def test_none_set_is_valid(self) -> None:
        # A bare volume with no path/config/efs_config is valid -- the
        # container-level `volumes:` mount-point syntax populates it later.
        v = Volume.model_validate({"name": "bare"})
        assert v.path is None
        assert v.config is None
        assert v.efs_config is None
