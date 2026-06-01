from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.cloudwatchlogs import (
    CloudWatchLogGroup,
    CloudWatchLogStream,
)


def _paginate(client: MagicMock, pages: list[dict]) -> None:
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = pages


class TestCloudWatchLogGroupManager:
    def test_list_log_groups(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(
            client,
            [{"logGroups": [{"logGroupName": "/ecs/app", "arn": "arn:logs:1"}]}],
        )
        groups = CloudWatchLogGroup.objects.list()
        assert len(groups) == 1
        assert groups[0].name == "/ecs/app"

    def test_get_log_group(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        client.describe_log_groups.return_value = {
            "logGroups": [{"logGroupName": "/ecs/app", "arn": "arn:logs:1"}],
        }
        group = CloudWatchLogGroup.objects.get("/ecs/app")
        assert group.pk == "/ecs/app"


class TestCloudWatchLogStreamManager:
    def test_list_streams(self, _mock_boto3_session: MagicMock) -> None:
        client = _mock_boto3_session
        _paginate(
            client,
            [
                {
                    "logStreams": [
                        {
                            "logStreamName": "stream/1",
                            "creationTime": 1000,
                        }
                    ]
                }
            ],
        )
        streams = CloudWatchLogStream.objects.list("/ecs/app")
        assert len(streams) == 1

    def test_newest_stream_from_group(self) -> None:
        group = CloudWatchLogGroup({"logGroupName": "/ecs/app", "arn": "arn:logs:1"})
        stream = CloudWatchLogStream(
            {"logGroupName": "/ecs/app", "logStreamName": "stream/new", "creationTime": 2000}
        )
        with patch.object(CloudWatchLogStream.objects, "list", return_value=[stream]):
            assert group.newest_stream() is stream
