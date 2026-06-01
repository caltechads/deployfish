import logging
from collections.abc import Generator
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ["tests.controller_helpers"]

from tests.fixtures import (
    APPLICATION_SCALING_YML,
    CONFIG_SECRETS_YML,
    FARGATE_SERVICE_YML,
    HELPER_TASKS_YML,
    SERVICE_YML,
    SERVICE_YML_WITH_HELPER_TASKS,
    SERVICE_YML_WITH_SCALING,
    STANDALONE_TASK_YML,
)

TESTS_DIR = Path(__file__).parent


@pytest.fixture(scope="session", autouse=True)
def _quiet_boto_logs() -> None:
    logging.getLogger("boto3").setLevel(logging.CRITICAL)
    logging.getLogger("botocore").setLevel(logging.CRITICAL)


@pytest.fixture(autouse=True)
def _mock_boto3_session() -> Generator[MagicMock, None, None]:
    """Prevent tests from calling live AWS APIs."""
    with patch("deployfish.core.models.abstract.get_boto3_session") as get_session:
        session = MagicMock()
        client = MagicMock()
        session.client.return_value = client
        get_session.return_value = session
        yield client


@pytest.fixture
def mock_boto3_session(_mock_boto3_session: MagicMock) -> MagicMock:
    """Alias underscore-prefixed boto fixture for tests that consume value."""
    return _mock_boto3_session


@pytest.fixture
def tests_dir() -> Path:
    return TESTS_DIR


@pytest.fixture
def service_yml() -> dict[str, Any]:
    return deepcopy(SERVICE_YML)


@pytest.fixture
def fargate_service_yml() -> dict[str, Any]:
    return deepcopy(FARGATE_SERVICE_YML)


@pytest.fixture
def standalone_task_yml() -> dict[str, Any]:
    return deepcopy(STANDALONE_TASK_YML)


@pytest.fixture
def helper_tasks_yml() -> dict[str, Any]:
    return deepcopy(HELPER_TASKS_YML)


@pytest.fixture
def application_scaling_yml() -> dict[str, Any]:
    return deepcopy(APPLICATION_SCALING_YML)


@pytest.fixture
def service_yml_with_scaling() -> dict[str, Any]:
    return deepcopy(SERVICE_YML_WITH_SCALING)


@pytest.fixture
def service_yml_with_helper_tasks() -> dict[str, Any]:
    return deepcopy(SERVICE_YML_WITH_HELPER_TASKS)


@pytest.fixture
def config_secrets_yml() -> list[str]:
    return list(CONFIG_SECRETS_YML)


@pytest.fixture
def minimal_deployfish_yml(tmp_path: Path, service_yml: dict[str, Any]) -> Path:
    path = tmp_path / "deployfish.yml"
    lines = [
        "services:",
        f"  - name: {service_yml['name']}",
        f"    cluster: {service_yml['cluster']}",
        f"    count: {service_yml['count']}",
        f"    family: {service_yml['family']}",
        f"    network_mode: {service_yml['network_mode']}",
        f"    task_role_arn: {service_yml['task_role_arn']}",
        "    containers:",
        "      - name: foobar",
        "        image: foobar/foobar:0.1.0",
        "        cpu: 512",
        "        memory: 512",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def mock_boto3_client() -> MagicMock:
    return MagicMock(name="boto3_client")
