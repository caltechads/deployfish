"""Coverage for TaskTagImporter/Exporter and VPCConfigurationMixin."""

from unittest.mock import MagicMock, patch

import pytest
from deployfish.core.models.ec2 import SecurityGroup, Subnet
from deployfish.core.models.ecs import (
    TaskTagExporter,
    TaskTagImporter,
    VPCConfigurationMixin,
)
from deployfish.exceptions import SchemaException


class _VpcHost(VPCConfigurationMixin):
    def __init__(self, data: dict) -> None:
        self.cache: dict = {}
        self.data = data


class TestVPCConfigurationMixin:
    def test_vpc_configuration_from_network_configuration(self) -> None:
        host = _VpcHost(
            {
                "networkConfiguration": {
                    "awsvpcConfiguration": {
                        "subnets": ["subnet-abc"],
                        "securityGroups": ["sg-abc"],
                        "allowPublicIp": True,
                    }
                }
            }
        )
        subnet = MagicMock()
        subnet.vpc = MagicMock()
        sg = MagicMock()
        with (
            patch.object(Subnet.objects, "get", return_value=subnet),
            patch.object(SecurityGroup.objects, "get", return_value=sg),
        ):
            config = host.vpc_configuration
        assert config["allow_public_ip"] is True
        assert config["subnets"] == [subnet]
        assert config["security_groups"] == [sg]

    def test_vpc_configuration_none_without_network(self) -> None:
        host = _VpcHost({})
        assert host.vpc_configuration is None


class TestTaskTagImporter:
    def test_convert_basic_deployfish_tags(self) -> None:
        tags = [
            {"key": "deployfish:service", "value": "cluster:svc"},
            {"key": "deployfish:type", "value": "standalone"},
            {"key": "deployfish:desiredCount", "value": "2"},
            {"key": "deployfish:task-name", "value": "my-task"},
            {"key": "deployfish:cluster", "value": "foobar-cluster"},
            {"key": "deployfish:launchType", "value": "FARGATE"},
            {"key": "deployfish:platformVersion", "value": "1.4.0"},
        ]
        data = TaskTagImporter().convert(tags)
        assert data["service"] == "cluster:svc"
        assert data["task_type"] == "standalone"
        assert data["count"] == 2
        assert data["name"] == "my-task"
        assert data["cluster"] == "foobar-cluster"
        assert data["launchType"] == "FARGATE"
        assert data["platformVersion"] == "1.4.0"

    def test_convert_capacity_provider_strategy(self) -> None:
        tags = [
            {
                "key": "deployfish:capacityProviderStrategy.0",
                "value": "provider=FARGATE_SPOT;weight=2;base=1",
            },
        ]
        data = TaskTagImporter().convert(tags)
        assert data["capacityProviderStrategy"][0]["capacityProvider"] == "FARGATE_SPOT"
        assert data["capacityProviderStrategy"][0]["weight"] == 2
        assert data["capacityProviderStrategy"][0]["base"] == 1

    def test_convert_placement_constraint_distinct_instance(self) -> None:
        tags = [
            {"key": "deployfish:placementConstraint.0", "value": "distinctInstance"}
        ]
        data = TaskTagImporter().convert(tags)
        assert data["placementConstraints"] == [{"type": "distinctInstance"}]

    def test_convert_placement_constraint_member_of_multipart(self) -> None:
        importer = TaskTagImporter()
        importer.data["placementConstraints"] = [
            {"type": "memberOf", "expression": "attribute:ecs.availability-zone"},
        ]
        importer._TaskTagImporter__convert_placementConstraint(  # type: ignore[attr-defined]
            "deployfish:placementConstraint.0.1",
            " == us-west-2a",
        )
        entry = importer.data["placementConstraints"][0]
        assert entry["type"] == "memberOf"
        assert "us-west-2a" in entry["expression"]

    def test_convert_placement_strategy_via_private_method(self) -> None:
        importer = TaskTagImporter()
        importer.data["placementStrategy"] = []
        importer._TaskTagImporter__convert_placementStrategy(  # type: ignore[attr-defined]
            "deployfish:placementStrategy.0",
            "field=instanceId;type=spread",
        )
        assert importer.data["placementStrategy"][0]["field"] == "instanceId"
        assert importer.data["placementStrategy"][0]["type"] == "spread"

    def test_convert_vpc_subnets_and_security_groups(self) -> None:
        tags = [
            {"key": "deployfish:vpc:subnet.0", "value": "subnet-a"},
            {"key": "deployfish:vpc:securityGroup.0", "value": "sg-a"},
            {"key": "deployfish:vpc:allowPublicIp", "value": "ENABLED"},
        ]
        data = TaskTagImporter().convert(tags)
        vpc = data["networkConfiguration"]["awsvpcConfiguration"]
        assert vpc["subnets"] == ["subnet-a"]
        assert vpc["securityGroups"] == ["sg-a"]
        assert vpc["allowPublicIp"] == "ENABLED"

    def test_invalid_placement_constraint_raises(self) -> None:
        importer = TaskTagImporter()
        with pytest.raises(SchemaException):
            importer._TaskTagImporter__convert_placementConstraint(  # type: ignore[attr-defined]
                "deployfish:placementConstraint.invalid",
                "bad",
            )


class TestTaskTagExporter:
    def test_convert_exports_task_metadata(self) -> None:
        data = {
            "name": "my-task",
            "cluster": "foobar-cluster",
            "count": 3,
            "service": "foobar-cluster:svc",
            "group": "batch",
            "launchType": "FARGATE",
            "platformVersion": "LATEST",
        }
        tags = TaskTagExporter().convert(data, task_type="standalone")
        assert tags["deployfish:task-name"] == "my-task"
        assert tags["deployfish:type"] == "standalone"
        assert tags["deployfish:desiredCount"] == "3"
        assert tags["deployfish:service"] == "foobar-cluster:svc"
        assert tags["deployfish:group"] == "batch"
        assert tags["deployfish:launchType"] == "FARGATE"

    def test_convert_capacity_provider_strategy(self) -> None:
        data = {
            "name": "t",
            "cluster": "c",
            "capacityProviderStrategy": [
                {"capacityProvider": "FARGATE", "weight": 1, "base": 0},
            ],
        }
        tags = TaskTagExporter().convert(data)
        assert "deployfish:capacityProvideStrategy.0" in tags

    def test_convert_long_member_of_constraint_splits(self) -> None:
        expression = "x" * 300
        data = {
            "name": "t",
            "cluster": "c",
            "placementConstraints": [{"type": "memberOf", "expression": expression}],
        }
        tags = TaskTagExporter().convert(data)
        assert "deployfish:placementConstraint.0.0" in tags

    def test_convert_distinct_instance_constraint(self) -> None:
        data = {
            "name": "t",
            "cluster": "c",
            "placementConstraints": [{"type": "distinctInstance"}],
        }
        tags = TaskTagExporter().convert(data)
        assert tags["deployfish:placementConstraint:expression.0"] == "distinctInstance"

    def test_convert_vpc_configuration(self) -> None:
        data = {
            "name": "t",
            "cluster": "c",
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": ["subnet-1"],
                    "securityGroups": ["sg-1"],
                    "allowPublicIp": "ENABLED",
                }
            },
        }
        tags = TaskTagExporter().convert(data)
        assert tags["deployfish:vpc:subnet.0"] == "subnet-1"
        assert tags["deployfish:vpc:securityGroup.0"] == "sg-1"
        assert tags["deployfish:vpc:allowPublicIp"] == "ENABLED"
