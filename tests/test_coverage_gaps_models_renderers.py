"""Coverage tests for elbv2 models, cloudwatch logs, renderers, jinja2, ecs adapters."""

from copy import deepcopy
from datetime import datetime
from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
import pytest
from deployfish.core.adapters.deployfish.ecs import (
    ContainerDefinitionAdapter,
    ServiceAdapter,
    VpcConfigurationMixin,
)
from deployfish.core.models.cloudwatchlogs import (
    CloudWatchLogGroup,
    CloudWatchLogGroupTailer,
    CloudWatchLogStream,
    CloudWatchLogStreamIterator,
    CloudWatchLogStreamTailer,
)
from deployfish.core.models.elbv2 import (
    LoadBalancer,
    LoadBalancerListener,
    LoadBalancerListenerRule,
    TargetGroup,
)
from deployfish.ext.ext_df_jinja2 import (
    DeployfishJinja2TemplateHandler,
    target_group_listener_rules,
)
from deployfish.renderers.table import LBListenerTableRenderer, TargetGroupTableRenderer

from tests.fixtures import FARGATE_SERVICE_YML, SERVICE_YML


class _VpcAdapter(VpcConfigurationMixin):
    def __init__(self, data: dict) -> None:
        self.data = data


class TestLoadBalancerRelatedProperties:
    def test_listeners_property_caches_listener_objects(self) -> None:
        lb = LoadBalancer(
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123:loadbalancer/app/test/abc",
                "LoadBalancerName": "test-lb",
                "DNSName": "test-lb.example.com",
                "VpcId": "vpc-123",
                "Type": "application",
                "Scheme": "internet-facing",
            }
        )
        listener = LoadBalancerListener(
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123:listener/app/test/abc/123",
                "LoadBalancerArn": lb.arn,
                "Port": 443,
                "Protocol": "HTTPS",
            }
        )
        with patch.object(
            LoadBalancerListener.objects, "list", return_value=[listener]
        ) as list_mock:
            assert lb.listeners == [listener]
            assert lb.listeners == [listener]
        list_mock.assert_called_once_with(load_balancer=lb.arn)


class TestTargetGroupRelatedProperties:
    def test_rules_property_lists_rules_for_target_group(self) -> None:
        tg = TargetGroup(
            {
                "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123:targetgroup/tg/abc",
                "TargetGroupName": "app-tg",
                "Port": 8080,
                "Protocol": "HTTP",
                "VpcId": "vpc-123",
                "LoadBalancerArns": [
                    "arn:aws:elasticloadbalancing:us-west-2:123:loadbalancer/app/test/abc"
                ],
            }
        )
        rule = LoadBalancerListenerRule(
            {
                "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123:listener-rule/app/test/abc/123",
                "Actions": [{"Type": "forward", "TargetGroupArn": tg.arn}],
            }
        )
        with patch.object(
            LoadBalancerListenerRule.objects, "list", return_value=[rule]
        ) as list_mock:
            assert tg.rules == [rule]
        list_mock.assert_called_once_with(target_group_arn=tg.arn)

    def test_listeners_property_collects_rule_and_default_listeners(self) -> None:
        tg = TargetGroup(
            {
                "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123:targetgroup/tg/abc",
                "TargetGroupName": "app-tg",
                "Port": 8080,
                "Protocol": "HTTP",
                "VpcId": "vpc-123",
                "LoadBalancerArns": [
                    "arn:aws:elasticloadbalancing:us-west-2:123:loadbalancer/app/test/abc"
                ],
            }
        )
        lb = LoadBalancer(
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123:loadbalancer/app/test/abc",
                "LoadBalancerName": "test-lb",
                "DNSName": "test-lb.example.com",
                "VpcId": "vpc-123",
                "Type": "application",
                "Scheme": "internet-facing",
            }
        )
        listener = LoadBalancerListener(
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123:listener/app/test/abc/123",
                "LoadBalancerArn": lb.arn,
                "Port": 443,
                "Protocol": "HTTPS",
                "DefaultActions": [
                    {"Type": "forward", "TargetGroupArn": tg.arn},
                ],
            }
        )
        rule = LoadBalancerListenerRule(
            {
                "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123:listener-rule/app/test/abc/456",
                "Actions": [{"Type": "forward", "TargetGroupArn": tg.arn}],
            },
            listener_arn=listener.arn,
        )
        with patch.object(
            LoadBalancerListenerRule.objects, "list", return_value=[rule]
        ), patch.object(LoadBalancer.objects, "get_many", return_value=[lb]):
            with patch.object(
                LoadBalancerListener.objects, "list", return_value=[listener]
            ):
                with patch.object(
                    LoadBalancerListener.objects, "get", return_value=listener
                ):
                    listeners = tg.listeners
        assert listener in listeners


class TestCloudWatchLogsIterators:
    def test_group_tailer_yields_new_events(self) -> None:
        group = CloudWatchLogGroup({"logGroupName": "/ecs/myapp", "arn": "arn:logs:1"})
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "events": [
                    {
                        "eventId": "1",
                        "timestamp": 1_700_000_000_000,
                        "message": "hello",
                    }
                ]
            }
        ]
        client = MagicMock()
        client.get_paginator.return_value = paginator
        with patch(
            "deployfish.core.models.cloudwatchlogs.get_boto3_session"
        ) as session_mock:
            session_mock.return_value.client.return_value = client
            tailer = CloudWatchLogGroupTailer(group, sleep=0)
            events = next(tailer)
        assert events[0]["message"] == "hello"
        assert isinstance(events[0]["timestamp"], datetime)

    def test_group_tailer_skips_duplicate_event_ids(self) -> None:
        group = CloudWatchLogGroup({"logGroupName": "/ecs/myapp", "arn": "arn:logs:1"})
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "events": [
                    {
                        "eventId": "1",
                        "timestamp": 1_700_000_000_000,
                        "message": "duplicate",
                    }
                ]
            }
        ]
        client = MagicMock()
        client.get_paginator.return_value = paginator
        with patch(
            "deployfish.core.models.cloudwatchlogs.get_boto3_session"
        ) as session_mock:
            session_mock.return_value.client.return_value = client
            tailer = CloudWatchLogGroupTailer(group, sleep=0)
            tailer.last_event_ids = ["1"]
            events = next(tailer)
        assert events == []

    def test_stream_tailer_yields_events(self) -> None:
        stream = CloudWatchLogStream(
            {
                "logGroupName": "/ecs/myapp",
                "logStreamName": "stream/abc",
                "lastEventTimestamp": 1_700_000_000_000,
            }
        )
        client = MagicMock()
        client.get_log_events.return_value = {
            "events": [
                {
                    "timestamp": 1_700_000_000_001,
                    "message": "tail-line",
                }
            ]
        }
        with patch(
            "deployfish.core.models.cloudwatchlogs.get_boto3_session"
        ) as session_mock:
            session_mock.return_value.client.return_value = client
            tailer = CloudWatchLogStreamTailer(stream, sleep=0)
            events = next(tailer)
        assert events[0]["message"] == "tail-line"

    def test_stream_iterator_stops_on_repeated_token(self) -> None:
        stream = CloudWatchLogStream(
            {
                "logGroupName": "/ecs/myapp",
                "logStreamName": "stream/abc",
            }
        )
        client = MagicMock()
        client.get_log_events.return_value = {
            "events": [],
            "nextForwardToken": "same-token",
        }
        with patch(
            "deployfish.core.models.cloudwatchlogs.get_boto3_session"
        ) as session_mock:
            session_mock.return_value.client.return_value = client
            iterator = CloudWatchLogStreamIterator(stream, sleep=0)
            iterator.kwargs["nextToken"] = "same-token"
            with pytest.raises(StopIteration):
                next(iterator)


class TestTargetGroupTableRendererGaps:
    def test_render_load_balancers_value(self) -> None:
        tg = MagicMock()
        lb = MagicMock()
        lb.name = "public-lb"
        tg.load_balancers = [lb]
        renderer = TargetGroupTableRenderer({})
        assert renderer.render_load_balancers_value(tg, "lb", "lb") == "public-lb"

    def test_render_targets_value(self) -> None:
        tg = MagicMock()
        target = MagicMock()
        target.target.name = "i-abc123"
        tg.targets = [target]
        renderer = TargetGroupTableRenderer({})
        assert renderer.render_targets_value(tg, "targets", "targets") == "i-abc123"

    def test_render_rules_value(self) -> None:
        tg = MagicMock()
        with patch(
            "deployfish.renderers.table.target_group_listener_rules",
            return_value="path:/api",
        ):
            renderer = TargetGroupTableRenderer({})
            assert renderer.render_rules_value(tg, "rules", "rules") == "path:/api"

    def test_render_listener_port_value(self) -> None:
        tg = MagicMock()
        listener = MagicMock()
        listener.protocol = "HTTPS"
        listener.port = 443
        tg.listeners = [listener]
        renderer = TargetGroupTableRenderer({})
        assert renderer.render_listener_port_value(tg, "port", "port") == "HTTPS:443"


class TestLBListenerTableRendererGaps:
    def test_render_default_action_forward_and_redirect(self) -> None:
        listener = LoadBalancerListener(
            {
                "ListenerArn": "arn:listener/1",
                "LoadBalancerArn": "arn:lb/1",
                "Port": 443,
                "Protocol": "HTTPS",
                "DefaultActions": [
                    {"Type": "forward", "TargetGroupArn": "arn:tg/1"},
                    {
                        "Type": "redirect",
                        "RedirectConfig": {
                            "StatusCode": "HTTP_301",
                            "Protocol": "HTTPS",
                            "Host": "example.com",
                            "Port": "443",
                            "Query": "a=1",
                        },
                    },
                    {
                        "Type": "fixed",
                        "FixedResponseConfig": {
                            "StatusCode": "404",
                            "ContentType": "text/plain",
                        },
                    },
                ],
            }
        )
        tg = MagicMock()
        tg.name = "app-tg"
        renderer = LBListenerTableRenderer({})
        with patch.object(TargetGroup.objects, "get", return_value=tg):
            output = renderer.render_default_action_value(listener, "action", "action")
        assert "forward:app-tg" in output
        assert "redirect[301]:https://example.com:443/?a=1" in output
        assert "fixed[404]: text/plain" in output

    def test_render_certificates_value(self) -> None:
        listener = LoadBalancerListener(
            {
                "ListenerArn": "arn:listener/1",
                "LoadBalancerArn": "arn:lb/1",
                "Port": 443,
                "Protocol": "HTTPS",
                "Certificates": [
                    {
                        "CertificateArn": "arn:aws:acm:us-west-2:123:certificate/abc",
                        "IsDefault": True,
                    }
                ],
            }
        )
        renderer = LBListenerTableRenderer({})
        with patch(
            "deployfish.renderers.table.click.style", side_effect=lambda v, **_: v
        ):
            output = renderer.render_certificates_value(listener, "certs", "certs")
        assert "[Default]" in output
        assert "abc" in output


class TestExtJinja2RemainingFilters:
    def test_target_group_listener_rules_fallback_forward(self) -> None:
        tg = MagicMock()
        tg.rules = []
        lb = MagicMock()
        lb.lb_type = "ALB"
        tg.load_balancers = [lb]
        listener = MagicMock()
        listener.port = 443
        listener.protocol = "HTTPS"
        tg.listeners = [listener]
        tg.port = 8080
        tg.protocol = "HTTP"
        result = target_group_listener_rules(tg)
        assert "forward:ALB:443:HTTPS" in result
        assert "CONTAINER:8080:HTTP" in result

    def test_target_group_listener_rules_query_and_method(self) -> None:
        tg = MagicMock()
        rule = MagicMock()
        rule.data = {
            "Conditions": [
                {"QueryStringConfig": {"Values": [{"Key": "q", "Value": "1"}]}},
                {"HttpRequestMethod": {"Values": ["POST"]}},
                {"SourceIpConfig": {"Values": ["10.0.0.0/8"]}},
            ]
        }
        tg.rules = [rule]
        result = target_group_listener_rules(tg)
        assert "qs:q=1" in result
        assert "verb:POST" in result
        assert "ip:10.0.0.0/8" in result

    def test_template_handler_registers_filters(self) -> None:
        handler = DeployfishJinja2TemplateHandler()
        handler.env = MagicMock()
        handler.env.filters = {}
        with patch(
            "deployfish.ext.ext_df_jinja2.Jinja2TemplateHandler.load",
            return_value=("content", "jinja2", "path"),
        ):
            handler.load("template.jinja2")
        registered = set(handler.env.filters.keys())
        assert {
            "color",
            "section_title",
            "fromtimestamp",
            "tabular",
            "target_group_table",
        }.issubset(registered)


class TestECSAdapterAdditionalMethods:
    def test_get_load_balancers_from_target_groups(self) -> None:
        adapter = ServiceAdapter(deepcopy(SERVICE_YML))
        load_balancers = adapter.get_loadBalancers()
        assert load_balancers[0]["targetGroupArn"] == "MY_TARGET_GROUP_ARN"
        assert load_balancers[0]["containerPort"] == 8080

    def test_get_load_balancers_elb_name(self) -> None:
        data = deepcopy(SERVICE_YML)
        data["load_balancer"] = {
            "load_balancer_name": "classic-elb",
            "container_name": "foobar",
            "container_port": 8080,
        }
        adapter = ServiceAdapter(data)
        load_balancers = adapter.get_loadBalancers()
        assert load_balancers[0]["loadBalancerName"] == "classic-elb"

    def test_get_vpc_configuration_maps_fields(self) -> None:
        adapter = _VpcAdapter(deepcopy(FARGATE_SERVICE_YML))
        config = adapter.get_vpc_configuration()
        assert config["subnets"] == ["subnet-abc123"]
        assert config["securityGroups"] == ["sg-abc123"]
        assert config["assignPublicIp"] == "DISABLED"

    def test_container_adapter_linux_parameters_and_hosts(self) -> None:
        container_data = {
            "name": "app",
            "image": "app:1",
            "cap_add": ["NET_ADMIN"],
            "cap_drop": ["SYS_ADMIN"],
            "tmpfs": [{"container_path": "/run", "size": 64}],
            "extra_hosts": ["db:10.0.0.5"],
            "logging": {
                "driver": "awslogs",
                "options": {"awslogs-group": "grp"},
            },
        }
        adapter = ContainerDefinitionAdapter(
            container_data, task_definition_data={"cpu": 1024, "memory": 2048}
        )
        linux = adapter.get_linuxParameters()
        assert linux["capabilities"]["add"] == ["NET_ADMIN"]
        assert adapter.get_extraHosts() == [{"hostname": "db", "ipAddress": "10.0.0.5"}]
        assert adapter.get_logConfiguration()["logDriver"] == "awslogs"

    def test_container_adapter_log_configuration_requires_driver(self) -> None:
        adapter = ContainerDefinitionAdapter(
            {"name": "app", "logging": {"options": {}}}
        )
        with pytest.raises(adapter.SchemaException, match='must contain "driver"'):
            adapter.get_logConfiguration()
