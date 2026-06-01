from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest
from deployfish.controllers.service import (
    ECSService,
    ECSServiceStandaloneTasks,
    valid_date,
)
from deployfish.core.models.ecs import Service

from tests.controller_helpers import bind_controller, bind_service_loader
from tests.fixtures import SERVICE_YML


class TestValidDate:
    def test_valid_date_parses(self) -> None:
        result = valid_date("2026-06-01")
        assert result.year == 2026

    def test_valid_date_rejects_bad_input(self) -> None:
        with pytest.raises(Exception):
            valid_date("not-a-date")


class TestECSServiceControllerExtended:
    def test_list_renders_services(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        with patch.object(Service.objects, "list", return_value=[]):
            controller.list()
        cement_app.print.assert_called_once()

    def test_plan_renders_diff(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        service = Service.new(deepcopy(SERVICE_YML), "deployfish")
        service.appscaling = None
        service.data["cluster"] = "foobar-cluster"
        service.data["serviceName"] = "foobar-test"
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_deployfish", return_value=service):
            with patch.object(loader, "get_object_from_aws", return_value=service):
                controller.plan()
        cement_app.render.assert_called_once()

    def test_info_renders_service(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSService(), cement_app)
        cement_app.pargs.pk = "foobar-cluster:foobar-test"
        mock_service = MagicMock()
        loader = bind_service_loader(controller)
        with patch.object(loader, "get_object_from_aws", return_value=mock_service):
            controller.info()
        cement_app.render.assert_called_once()


class TestECSServiceStandaloneTasksController:
    def test_list_related_tasks(self, cement_app: MagicMock) -> None:
        controller = bind_controller(ECSServiceStandaloneTasks(), cement_app)
        cement_app.pargs.pk = "foobar-test"
        mock_service = MagicMock()
        mock_service.pk = "foobar-cluster:foobar-test"
        mock_service.name = "foobar-test"
        loader = bind_service_loader(controller)
        cement_app.deployfish_config.cooked = {"tasks": []}
        with patch.object(
            loader, "get_object_from_deployfish", return_value=mock_service
        ):
            controller.list_related_tasks()
        cement_app.print.assert_called_once_with("No related tasks.")
