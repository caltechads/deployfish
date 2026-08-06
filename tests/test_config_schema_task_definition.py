"""Tests for the TaskDefinitionInput sub-models."""

import pytest
from deployfish.config.schema.task_definition import (
    TaskDefinitionInput,
    TaskDefinitionOverlayInput,
    Volume,
)
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


class TestTaskDefinitionInputVolumes:
    def test_duplicate_volume_names_raise(self) -> None:
        with pytest.raises(ValidationError, match='duplicate volume name "dup"'):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "containers": [{"name": "web", "image": "nginx:1.25"}],
                    "volumes": [
                        {"name": "dup", "path": "/a"},
                        {"name": "dup", "path": "/b"},
                    ],
                }
            )

    def test_unique_volume_names_pass(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "containers": [{"name": "web", "image": "nginx:1.25"}],
                "volumes": [
                    {"name": "a", "path": "/a"},
                    {"name": "b", "path": "/b"},
                ],
            }
        )
        assert [v.name for v in td.volumes] == ["a", "b"]


class TestTaskDefinitionInputContainers:
    def test_composes_container_definition_input(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "containers": [
                    {"name": "web", "image": "nginx:1.25", "cpu": 128, "memory": 256}
                ],
            }
        )
        assert len(td.containers) == 1
        assert td.containers[0].name == "web"
        assert td.containers[0].image == "nginx:1.25"

    def test_missing_containers_key_raises_custom_message(self) -> None:
        with pytest.raises(
            ValidationError, match="at least one container in your task definition"
        ):
            TaskDefinitionInput.model_validate({"family": "web"})

    def test_container_cpu_greater_than_task_cpu_raises(self) -> None:
        with pytest.raises(ValidationError, match="cpu is greater than the task cpu"):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "cpu": 256,
                    "containers": [
                        {
                            "name": "web",
                            "image": "nginx:1.25",
                            "cpu": 512,
                            "memory": 256,
                        }
                    ],
                }
            )

    def test_container_memory_greater_than_task_memory_raises(self) -> None:
        with pytest.raises(ValidationError, match="memory is greater than task memory"):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "memory": 256,
                    "containers": [
                        {
                            "name": "web",
                            "image": "nginx:1.25",
                            "cpu": 128,
                            "memory": 512,
                        }
                    ],
                }
            )

    def test_container_cpu_within_task_cpu_passes(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "cpu": 512,
                "containers": [
                    {"name": "web", "image": "nginx:1.25", "cpu": 256, "memory": 256}
                ],
            }
        )
        assert td.cpu == 512  # noqa: PLR2004

    def test_fargate_without_execution_role_raises(self) -> None:
        with pytest.raises(ValidationError, match='"execution_role"'):
            TaskDefinitionInput.model_validate(
                {
                    "family": "web",
                    "launch_type": "FARGATE",
                    "containers": [{"name": "web", "image": "nginx:1.25"}],
                }
            )

    def test_fargate_with_execution_role_passes(self) -> None:
        td = TaskDefinitionInput.model_validate(
            {
                "family": "web",
                "launch_type": "FARGATE",
                "execution_role": "MY_ROLE",
                "containers": [{"name": "web", "image": "nginx:1.25"}],
            }
        )
        assert td.execution_role == "MY_ROLE"


class TestTaskDefinitionOverlayInput:
    def test_all_fields_optional(self) -> None:
        overlay = TaskDefinitionOverlayInput.model_validate({})
        assert overlay.family is None
        assert overlay.containers is None

    def test_partial_container_overrides_allowed(self) -> None:
        # A ServiceHelperTask command override: only name + command, no image.
        overlay = TaskDefinitionOverlayInput.model_validate(
            {"containers": [{"name": "foobar", "command": "./manage.py migrate"}]}
        )
        assert overlay.containers[0].name == "foobar"
        assert overlay.containers[0].image is None

    def test_missing_containers_does_not_raise(self) -> None:
        # Unlike the strict model, omitting "containers" entirely is fine.
        overlay = TaskDefinitionOverlayInput.model_validate({"family": "web"})
        assert overlay.containers is None

    def test_fargate_without_execution_role_does_not_raise(self) -> None:
        # The strict model's FARGATE/execution_role requirement does not
        # apply to overlay/partial data.
        overlay = TaskDefinitionOverlayInput.model_validate(
            {"launch_type": "FARGATE"}
        )
        assert overlay.execution_role is None
