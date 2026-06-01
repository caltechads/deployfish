import contextlib
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from deployfish.core.aws import get_boto3_session

from .abstract import Manager, Model


def _event_timestamp_to_utc(timestamp_ms: int) -> datetime:
    """
    Convert CloudWatch millisecond timestamps to aware UTC datetimes.

    Args:
        timestamp_ms: Epoch timestamp in milliseconds.

    Returns:
        Timezone-aware UTC datetime for CloudWatch event timestamp.

    """
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)


def _default_start_time_ms(sleep: int) -> int:
    """
    Compute default tail start time in milliseconds.

    Args:
        sleep: Polling interval in seconds.

    Returns:
        Epoch milliseconds representing one poll interval ago.

    """
    return int((datetime.now(tz=UTC).timestamp() - sleep) * 1000)


class CloudWatchLogStreamIterator:
    """
    An iterator class that allows you to iterate through your cloudwatch logs
    from a log stream.

    Args:
        stream: the log stream to iterate through

    Keyword Args:
        sleep: the number of seconds to sleep between requests
        start_time: the time to start the iterator from

    """

    def __init__(
        self,
        stream: "CloudWatchLogStream",
        sleep: int = 5,
        start_time: datetime | None = None,
    ) -> None:
        """
        :param start_time datetime: a timezone aware, UTC datetime
        """
        self.client = get_boto3_session().client("logs")
        self.kwargs = {
            "logGroupName": stream.data["logGroupName"],
            "logStreamName": stream.name,
            "startFromHead": True,
        }
        if start_time is not None:
            self.kwargs["startTime"] = int(start_time.timestamp() * 1000)
        self.sleep = sleep

    def __iter__(self) -> "CloudWatchLogStreamIterator":
        return self

    def __next__(self) -> list[dict[str, Any]]:
        if "nextToken" in self.kwargs:
            # Don't sleep on the first iteration
            time.sleep(self.sleep)
        response = self.client.get_log_events(**self.kwargs)
        events = []
        for event in response["events"]:
            event["timestamp"] = _event_timestamp_to_utc(event["timestamp"])
            events.append(event)
        token = response["nextForwardToken"]
        if "nextToken" in self.kwargs and token == self.kwargs["nextToken"]:
            raise StopIteration
        self.kwargs["nextToken"] = token
        return events


class CloudWatchLogGroupTailer:
    """
    An iterator class that allows you to tail live logs from a CloudWatchLogStream.
    """

    def __init__(
        self,
        group: "CloudWatchLogGroup",
        stream_prefix: str | None = None,
        sleep: int = 5,
        filter_pattern: str | None = None,
        start_time: int | None = None,
    ):
        self.client = get_boto3_session().client("logs")
        self.kwargs: dict[str, Any] = {"logGroupName": group.name}
        if stream_prefix:
            self.kwargs["logStreamNamePrefix"] = stream_prefix
        if filter_pattern:
            self.kwargs["filterPattern"] = filter_pattern
        # startTime is milliseconds since Jan 1, 1970 00:00:00 UTC
        if start_time:
            self.kwargs["startTime"] = start_time - (1000 * sleep)
        else:
            self.kwargs["startTime"] = _default_start_time_ms(sleep)
        self.sleep: int = sleep
        self.last_event_ids: list[str] = []
        self.started: bool = False

    def __iter__(self) -> "CloudWatchLogGroupTailer":
        return self

    def __next__(self) -> list[dict[str, Any]]:
        if not self.started:
            # Don't sleep on the first iteration
            self.started = True
        else:
            time.sleep(self.sleep)
        if not self.last_event_ids:
            self.kwargs["startTime"] += self.sleep * 1000
        paginator = self.client.get_paginator("filter_log_events")
        response_iterator = paginator.paginate(**self.kwargs)
        events = []
        for response in response_iterator:
            for event in response["events"]:
                event["raw_timestamp"] = event["timestamp"]
                event["timestamp"] = _event_timestamp_to_utc(event["timestamp"])
                if event["eventId"] not in self.last_event_ids:
                    events.append(event)
        if events:
            self.kwargs["startTime"] = events[-1]["raw_timestamp"]
            self.last_event_ids = [e["eventId"] for e in events]
        return events


class CloudWatchLogStreamTailer:
    """
    An iterator class that allows you to tail live logs from a CloudWatchLogStream.
    """

    def __init__(self, stream: "CloudWatchLogStream", sleep: int = 5):
        """
        :param start_time datetime: a timezone aware, UTC datetime
        """
        self.client = get_boto3_session().client("logs")
        self.kwargs: dict[str, Any] = {
            "logGroupName": stream.data["logGroupName"],
            "logStreamName": stream.name,
        }
        # startTime is milliseconds since Jan 1, 1970 00:00:00 UTC
        if "lastEventTimestamp" in stream.data:
            self.kwargs["startTime"] = stream.data["lastEventTimestamp"] - (
                1000 * sleep
            )
        else:
            self.kwargs["startTime"] = _default_start_time_ms(sleep)
        self.sleep: int = sleep
        self.last_event: dict[str, Any] | None = None

    def __iter__(self) -> "CloudWatchLogStreamTailer":
        return self

    def __next__(self) -> list[dict[str, Any]]:
        if self.last_event:
            # Don't sleep on the first iteration
            time.sleep(self.sleep)
        response = self.client.get_log_events(**self.kwargs)
        events = []
        for event in response["events"]:
            event["raw_timestamp"] = event["timestamp"]
            event["timestamp"] = _event_timestamp_to_utc(event["timestamp"])
            # get_log_events omits eventId, so tailer falls back to full-event
            # equality to avoid duplicating repeated entries.
            if event != self.last_event:
                events.append(event)
        if events:
            self.kwargs["startTime"] = events[-1]["raw_timestamp"]
            self.last_event = events[-1]
        return events


# ----------------------------------------
# Managers
# ----------------------------------------


class CloudWatchLogGroupManager(Manager):
    service = "logs"

    def get(self, pk: str, **_) -> "CloudWatchLogGroup":
        response = self.client.describe_log_groups(logGroupNamePrefix=pk)
        for group in response["logGroups"]:
            if group["logGroupName"] == pk:
                return CloudWatchLogGroup(group)
        msg = f"No CloudWatchLogGroup matching pk={pk} exists in AWS."
        raise CloudWatchLogGroup.DoesNotExist(msg)

    def list(self, prefix: str | None = None) -> Sequence["CloudWatchLogGroup"]:
        paginator = self.client.get_paginator("describe_log_groups")
        kwargs = {}
        if prefix:
            kwargs["logGroupNamePrefix"] = prefix
        response_iterator = paginator.paginate(**kwargs)
        group_data = []
        for response in response_iterator:
            group_data.extend(response["logGroups"])
        return [CloudWatchLogGroup(data) for data in group_data]


class CloudWatchLogStreamManager(Manager):
    service = "logs"

    def __get_group_and_stream_from_pk(self, pk: str) -> list[str]:
        return pk.split(":", 1)

    def get(self, pk: str, **_) -> "CloudWatchLogStream":
        group_name, stream_name = self.__get_group_and_stream_from_pk(pk)
        response = self.client.describe_log_streams(
            logGroupName=group_name, logStreamNamePrefix=stream_name
        )
        if len(response["logStreams"]) > 1:
            msg = f"Got more than one log stream when searching for pk={pk}"
            raise CloudWatchLogStream.MultipleObjectsReturned(msg)
        if len(response["logStreams"]) == 0:
            msg = f"No CloudWatchLogStream matching pk={pk} exists in AWS."
            raise CloudWatchLogStream.DoesNotExist(msg)
        data = response["logStreams"][0]
        data["logGroupName"] = group_name
        return CloudWatchLogStream(data)

    def list(
        self, log_group_name: str, prefix: str | None = None, limit: int | None = None
    ) -> Sequence["CloudWatchLogStream"]:
        """
        .. note::

            ``log_group_name`` stays required because listing every stream in
            every group would be too large for typical deployfish usage.
        """
        paginator = self.client.get_paginator("describe_log_streams")
        kwargs: dict[str, Any] = {"logGroupName": log_group_name}
        if prefix:
            kwargs["logStreamNamePrefix"] = prefix
        else:
            kwargs["orderBy"] = "LastEventTime"
            kwargs["descending"] = True
        response_iterator = paginator.paginate(**kwargs)
        stream_data = []
        for response in response_iterator:
            for stream in response["logStreams"]:
                stream["logGroupName"] = log_group_name
            stream_data.extend(response["logStreams"])
            if limit and len(stream_data) > limit:
                stream_data = stream_data[:limit]
                break
        streams = [CloudWatchLogStream(data) for data in stream_data]
        if prefix:
            streams = sorted(
                streams, key=lambda x: x.data.get("lastEventTimestamp", -1)
            )
            streams.reverse()
        return streams


# ----------------------------------------
# Models
# ----------------------------------------


class CloudWatchLogGroup(Model):
    #: Manager for CloudWatch log group records.
    objects = CloudWatchLogGroupManager()

    @property
    def pk(self) -> str:
        return self.data["logGroupName"]

    @property
    def name(self) -> str:
        return self.data["logGroupName"]

    @property
    def arn(self) -> str:
        return self.data["arn"]

    def newest_stream(
        self, prefix: str | None = None
    ) -> "CloudWatchLogStream | None":
        """
        Return most recent stream in this group.

        Args:
            prefix: Optional stream-name prefix filter.

        Returns:
            Most recent stream, or ``None`` when no matching stream exists.

        """
        try:
            return CloudWatchLogStream.objects.list(self.name, prefix=prefix)[0]
        except IndexError:
            return None

    def get_event_tailer(
        self,
        stream_prefix: str | None = None,
        sleep: int = 10,
        filter_pattern: str | None = None,
    ) -> CloudWatchLogGroupTailer:
        """
        Build live tailer for this log group.

        Args:
            stream_prefix: Optional stream-name prefix filter.
            sleep: Poll interval in seconds.
            filter_pattern: Optional CloudWatch Logs filter pattern.

        Returns:
            Iterator that tails matching events from group streams.

        """
        newest_stream = self.newest_stream(prefix=stream_prefix)
        start_time = None
        if newest_stream:
            with contextlib.suppress(KeyError):
                start_time = newest_stream.data["lastEventTimestamp"]
        return CloudWatchLogGroupTailer(
            self,
            stream_prefix=stream_prefix,
            sleep=sleep,
            filter_pattern=filter_pattern,
            start_time=start_time,
        )

    def log_streams(
        self, stream_prefix: str | None = None, maxitems: int | None = None
    ) -> Sequence["CloudWatchLogStream"]:
        """
        List streams in this log group.

        Args:
            stream_prefix: Optional stream-name prefix filter.
            maxitems: Maximum number of streams to return.

        Returns:
            Matching log streams, newest first when AWS supports ordering.

        """
        return CloudWatchLogStream.objects.list(
            self.pk, prefix=stream_prefix, limit=maxitems
        )


class CloudWatchLogStream(Model):
    #: Manager for CloudWatch log stream records.
    objects = CloudWatchLogStreamManager()

    @property
    def pk(self) -> str:
        return f"{self.data['logGroupName']}:{self.data['logStreamName']}"

    @property
    def name(self) -> str:
        return self.data["logStreamName"]

    @property
    def arn(self) -> str:
        return self.data["arn"]

    @property
    def log_group(self) -> CloudWatchLogGroup:
        """
        Return parent log group for this stream.

        Returns:
            Parent log group.

        """
        return self.get_cached(
            "log_group", CloudWatchLogGroup.objects.get, [self.data["logGroupName"]]
        )

    def get_event_tailer(self, sleep: int = 10) -> CloudWatchLogStreamTailer:
        """
        Build live tailer for this log stream.

        Args:
            sleep: Poll interval in seconds.

        Returns:
            Tailer configured for this stream.

        """
        return CloudWatchLogStreamTailer(self, sleep)

    def events(self, sleep: int = 10) -> CloudWatchLogStreamIterator:
        """
        Iterate through stream events from oldest to newest.

        Args:
            sleep: Poll interval in seconds.

        Returns:
            Iterator over paged log events.

        """
        return CloudWatchLogStreamIterator(self, sleep)
