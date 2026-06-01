from unittest.mock import MagicMock, patch

import deployfish.core.adapters  # noqa: F401
from deployfish.core.models.cloudwatchlogs import (
    CloudWatchLogGroup,
    CloudWatchLogGroupTailer,
    CloudWatchLogStream,
    CloudWatchLogStreamIterator,
)
from deployfish.core.utils.utils import is_fnmatch_filter


class TestCloudWatchLogGroup:
    def test_name_and_pk(self) -> None:
        group = CloudWatchLogGroup({"logGroupName": "/ecs/myapp", "arn": "arn:logs:1"})
        assert group.name == "/ecs/myapp"
        assert group.pk == "/ecs/myapp"

    def test_get_event_tailer(self) -> None:
        group = CloudWatchLogGroup({"logGroupName": "/ecs/myapp", "arn": "arn:logs:1"})
        tailer = group.get_event_tailer(
            stream_prefix="prefix", sleep=5, filter_pattern="ERROR"
        )
        assert isinstance(tailer, CloudWatchLogGroupTailer)
        assert tailer.kwargs["logStreamNamePrefix"] == "prefix"
        assert tailer.kwargs["filterPattern"] == "ERROR"

    def test_newest_stream_returns_none_when_empty(self) -> None:
        group = CloudWatchLogGroup({"logGroupName": "/ecs/myapp", "arn": "arn:logs:1"})
        with patch.object(CloudWatchLogStream.objects, "list", return_value=[]):
            assert group.newest_stream() is None


class TestCloudWatchLogStream:
    def test_stream_name_property(self) -> None:
        stream = CloudWatchLogStream(
            {
                "logGroupName": "/ecs/myapp",
                "logStreamName": "stream/abc",
                "creationTime": 1000,
            }
        )
        assert stream.name == "stream/abc"
        assert stream.pk == "/ecs/myapp:stream/abc"


class TestCloudWatchLogStreamIterator:
    def test_iterator_yields_events(self) -> None:
        stream = CloudWatchLogStream(
            {
                "logGroupName": "/ecs/myapp",
                "logStreamName": "stream/abc",
            }
        )
        client = MagicMock()
        client.get_log_events.return_value = {
            "events": [{"timestamp": 1_700_000_000_000, "message": "hello"}],
            "nextForwardToken": "token-1",
        }
        with patch(
            "deployfish.core.models.cloudwatchlogs.get_boto3_session"
        ) as session_mock:
            session_mock.return_value.client.return_value = client
            iterator = CloudWatchLogStreamIterator(stream, sleep=0)
            events = next(iterator)
        assert len(events) == 1
        assert events[0]["message"] == "hello"


class TestUtils:
    def test_is_fnmatch_filter_detects_glob(self) -> None:
        assert is_fnmatch_filter("prod-*") is True
        assert is_fnmatch_filter("exact-name") is False
        assert is_fnmatch_filter(None) is False
