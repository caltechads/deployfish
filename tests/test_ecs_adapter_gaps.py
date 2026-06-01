from copy import deepcopy

import deployfish.core.adapters  # noqa: F401
from deployfish.core.adapters.deployfish.ecs import ServiceAdapter

from tests.fixtures import FARGATE_SERVICE_YML, SERVICE_YML


class TestECSAdapterGaps:
    def test_service_adapter_client_token_deterministic(self) -> None:
        adapter = ServiceAdapter(deepcopy(SERVICE_YML))
        first = adapter.get_clientToken()
        second = adapter.get_clientToken()
        assert first == second

    def test_fargate_adapter_sets_launch_type(self) -> None:
        adapter = ServiceAdapter(deepcopy(FARGATE_SERVICE_YML))
        _service_data, kwargs = adapter.convert()
        assert (
            kwargs.get("launch_type") == "FARGATE"
            or _service_data.get("launchType") == "FARGATE"
        )

    def test_service_adapter_includes_task_definition(self) -> None:
        adapter = ServiceAdapter(deepcopy(SERVICE_YML))
        _service_data, kwargs = adapter.convert()
        assert "task_definition" in kwargs
