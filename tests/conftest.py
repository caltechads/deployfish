import logging
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent


@pytest.fixture(scope="session", autouse=True)
def _quiet_boto_logs() -> None:
    logging.getLogger("boto3").setLevel(logging.CRITICAL)
    logging.getLogger("botocore").setLevel(logging.CRITICAL)


@pytest.fixture
def tests_dir() -> Path:
    return TESTS_DIR
