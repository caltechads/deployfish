from datetime import datetime, timezone
import time

from deployfish.core.aws import get_boto3_session
from .abstract import Manager, Model


class CloudWatchLogStreamIterator(object):
    """
    An iterator class that allows you to iterate through your cloudwatch logs from a log stream.
    """

    def __init__(self, stream, sleep=5, start_time=None):
        """
        :param start_time datetime: a timezone aware, UTC datetime
        """
        self.client = get_boto3_session().client('logs')
        self.kwargs = {
            'logGroupName': stream.data['logGroupName'],
            'logStreamName': stream.name,
            'startFromHead': True
        }
        self.sleep = sleep

    def __iter__(self):
        return self

    def __next__(self):
        if 'nextToken' in self.kwargs:
            # Don't sleep on the first iteration
            time.sleep(self.sleep)
        response = self.client.get_log_events(**self.kwargs)
        events = []
        for event in response['events']:
            # Just convert our timetamp to something more useful
            event['timestamp'] = datetime.fromtimestamp(event['timestamp'] / 1000.0)
            events.append(event)
        token = response['nextForwardToken']
        if 'nextToken' in self.kwargs and token == self.kwargs['nextToken']:
            raise StopIteration
        self.kwargs['nextToken'] = token
        return events


class CloudWatchLogGroupTailer(object):
    """
    An iterator class that allows you to tail live logs from a CloudWatchLogStream.
    """

    def __init__(self, group, stream_prefix=None, sleep=5, filter_pattern=None, start_time=None):
        self.client = get_boto3_session().client('logs')
        self.kwargs = {'logGroupName': group.name}
        if stream_prefix:
            self.kwargs['logStreamNamePrefix'] = stream_prefix
        if filter_pattern:
            self.kwargs['filterPattern'] = filter_pattern
        # startTime is milliseconds since Jan 1, 1970 00:00:00 UTC
        if start_time:
            self.kwargs['startTime'] = start_time - (1000 * sleep)
        else:
            self.kwargs['startTime'] = int(((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() - sleep) * 1000)
        self.sleep = sleep
        self.last_event_ids = []
        self.started = False

    def __iter__(self):
        return self

    def __next__(self):
        if not self.started:
            # Don't sleep on the first iteration
            self.started = True
        else:
            time.sleep(self.sleep)
        if not self.last_event_ids:
            self.kwargs['startTime'] += self.sleep * 1000
        paginator = self.client.get_paginator('filter_log_events')
        response_iterator = paginator.paginate(**self.kwargs)
        events = []
        for response in response_iterator:
            for event in response['events']:
                # Just convert our timetamp to something more useful
                event['raw_timestamp'] = event['timestamp']
                event['timestamp'] = datetime.fromtimestamp(event['timestamp'] / 1000.0)
                if event['eventId'] not in self.last_event_ids:
                    events.append(event)
        if events:
            self.kwargs['startTime'] = events[-1]['raw_timestamp']
            self.last_event_ids = [e['eventId'] for e in events]
        return events


class CloudWatchLogStreamTailer(object):
    """
    An iterator class that allows you to tail live logs from a CloudWatchLogStream.
    """

    def __init__(self, stream, sleep=5):
        """
        :param start_time datetime: a timezone aware, UTC datetime
        """
        self.client = get_boto3_session().client('logs')
        self.kwargs = {
            'logGroupName': stream.data['logGroupName'],
            'logStreamName': stream.name,
        }
        # startTime is milliseconds since Jan 1, 1970 00:00:00 UTC
        if 'lastEventTimestamp' in stream.data:
            self.kwargs['startTime'] = stream.data['lastEventTimestamp'] - (1000 * sleep)
        else:
            self.kwargs['startTime'] = int(((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() - sleep) * 1000)
        self.sleep = sleep
        self.last_event = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.last_event:
            # Don't sleep on the first iteration
            time.sleep(self.sleep)
        response = self.client.get_log_events(**self.kwargs)
        events = []
        for event in response['events']:
            # Just convert our timetamp to something more useful
            event['raw_timestamp'] = event['timestamp']
            event['timestamp'] = datetime.fromtimestamp(event['timestamp'] / 1000.0)
            # FIXME: what is dumb here is that get_log_events does not return the eventId, but filter_log_events does.
            # eventId is very useful for deduping
            if event != self.last_event:
                events.append(event)
        if events:
            self.kwargs['startTime'] = events[-1]['raw_timestamp']
            self.last_event = events[-1]
        return events

# ----------------------------------------
# Managers
# ----------------------------------------


class CloudWatchLogGroupManager(Manager):

    service = 'logs'

    def get(self, pk):
        # hint: (str["{log group name}"])
        response = self.client.describe_log_groups(
            logGroupNamePrefix=pk
        )
        if len(response['logGroups']) > 1:
            raise CloudWatchLogGroup.MultipleObjectsReturned(
                "Got more than one log group when searching for pk={}".format(
                    pk,
                    ", ".join([group for group in response['logGroups']])
                )
            )
        elif len(response['logGroups']) == 0:
            raise CloudWatchLogGroup.DoesNotExist(
                "No CloudWatchLogGroup matching pk={} exists in AWS.".format(pk)
            )
        return CloudWatchLogGroup(response['logGroups'][0])

    def list(self, prefix=None):
        # hint: (str)
        paginator = self.client.get_paginator('describe_log_groups')
        kwargs = {}
        if prefix:
            kwargs['logGroupNamePrefix'] = prefix
        response_iterator = paginator.paginate(**kwargs)
        group_data = []
        for response in response_iterator:
            group_data.extend(response['logGroups'])
        return [CloudWatchLogGroup(data) for data in group_data]

    def save(self, obj):
        raise CloudWatchLogGroup.ReadOnly('Cannot modify Application Load Balancers with deployfish')

    def delete(self, pk):
        raise CloudWatchLogGroup.ReadOnly('Cannot modify Application Load Balancers with deployfish')


class CloudWatchLogStreamManager(Manager):

    service = 'logs'

    def __get_group_and_stream_from_pk(self, pk):
        return pk.split(':', 1)

    def get(self, pk):
        # hint: (str["{log group name}:{log stream name}"])
        group_name, stream_name = self.__get_group_and_stream_from_pk(pk)
        response = self.client.describe_log_streams(
            logGroupName=group_name,
            logStreamNamePrefix=stream_name
        )
        if len(response['logStreams']) > 1:
            raise CloudWatchLogStream.MultipleObjectsReturned(
                "Got more than one log stream when searching for pk={}".format(
                    pk,
                    ", ".join([group for group in response['logGroups']])
                )
            )
        elif len(response['logStreams']) == 0:
            raise CloudWatchLogStream.DoesNotExist(
                "No CloudWatchLogStream matching pk={} exists in AWS.".format(pk)
            )
        data = response['logStreams'][0]
        data['logGroupName'] = group_name
        return CloudWatchLogStream(data)

    def list(self, log_group_name, prefix=None, maxitems=None):
        # hint: (str, str, int)
        """
        .. note::

            Note that ``log_group_name`` is required here.  We could turn this into "list all streams", but we in ADS
            have a bajillion groups and streams and that might be untenable to actually work with.
        """
        paginator = self.client.get_paginator('describe_log_streams')
        kwargs = {'logGroupName': log_group_name}
        if prefix:
            kwargs['logStreamNamePrefix'] = prefix
        else:
            kwargs['orderBy'] = 'LastEventTime'
            kwargs['descending'] = True
        response_iterator = paginator.paginate(**kwargs)
        stream_data = []
        for response in response_iterator:
            for stream in response['logStreams']:
                stream['logGroupName'] = log_group_name
            stream_data.extend(response['logStreams'])
            if maxitems and len(stream_data) > maxitems:
                stream_data = stream_data[:maxitems]
                break
        streams = [CloudWatchLogStream(data) for data in stream_data]
        if prefix:
            streams = sorted(streams, key=lambda x: x.data.get('lastEventTimestamp', -1))
            streams.reverse()
        return streams

    def save(self, obj):
        raise CloudWatchLogGroup.ReadOnly('Cannot modify Application Load Balancers with deployfish')

    def delete(self, pk):
        raise CloudWatchLogGroup.ReadOnly('Cannot modify Application Load Balancers with deployfish')


# ----------------------------------------
# Models
# ----------------------------------------

class CloudWatchLogGroup(Model):

    objects = CloudWatchLogGroupManager()

    @property
    def pk(self):
        return self.data['logGroupName']

    @property
    def name(self):
        return self.data['logGroupName']

    @property
    def arn(self):
        return self.data['arn']

    def newest_stream(self, prefix=None):
        """
        Look through all our streams and return the one that has the most recent message.  If there is no
        such stream, return None.

        :param prefix str: (optional) if provided, filter streams to only those name matches this prefix

        :rtype: Union[CloudWatchLogStream, None]
        """
        try:
            return CloudWatchLogStream.objects.list(self.name, prefix=prefix)[0]
        except IndexError:
            return None

    def get_event_tailer(self, stream_prefix=None, sleep=10, filter_pattern=None):
        # hint: (str["{log_stream_prefix}"], int, str["{filter_pattern}"])
        # help_str:stream_prefix:Filter log events to those from streams matching this prefix
        # help_str:sleep:Sleep for this many seconds between polls
        """
        Return a properly configured iterator that will eternally poll our log group (note -- not stream) for new
        messages in any of its streams, possibly filtering by log stream prefix and filter pattern.

        For ``filter_pattern`` syntax , see
        (https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html)_

        :param stream_prefix str: (optional) if provided, only poll messages from streams matching this prefix
        :param sleep int: (optional) if provided, sleep this long between polls
        :param filter_pattern: (optional) if provided, only return messages matching this filter

        :rtype: CloudWatchLogGroupTailer
        """
        return CloudWatchLogGroupTailer(
            self,
            stream_prefix=stream_prefix,
            sleep=sleep,
            filter_pattern=filter_pattern,
            start_time=self.newest_stream(prefix=stream_prefix).data['lastEventTimestamp']
        )

    def log_streams(self, stream_prefix=None, maxitems=None):
        """
        Retrun a list of all our log streams.

        :param stream_prefix str: (optional) if provided, only return streams matching this prefix
        :param maxitems Union[int, None]: (optional) if provided, limit the streams returned to the ``maxitems`` most
                                          recently updated ones

        :rtype: list(CloudWatchLogStream)
        """
        return CloudWatchLogStream.objects.list(
            self.pk,
            prefix=stream_prefix,
            maxitems=maxitems
        )


class CloudWatchLogStream(Model):

    objects = CloudWatchLogStreamManager()

    @property
    def pk(self):
        return "{}:{}".format(self.data['logGroupName'], self.data['logStreamName'])

    @property
    def name(self):
        return self.data['logStreamName']

    @property
    def arn(self):
        return self.data['arn']

    @property
    def log_group(self):
        """
        Return the ``CloudWatchLogGroup`` that we belong to.

        :rtype: CloudWatchLogGroup
        """
        return self.get_cached('log_group', CloudWatchLogGroup.objects.get, [self.data['logGroupName']])

    def get_event_tailer(self, sleep=10):
        # hint: (int)
        """
        Return a properly configured iterator that will eternally poll our log stream for new messages.

        :param sleep int: (optional) if provided, sleep this long between polls

        :rtype: CloudWatchLogStreamTailer
        """
        return CloudWatchLogStreamTailer(self, sleep)

    def events(self, sleep=10):
        # hint: (int)
        """
        Return a properly configured iterator that will page through all the events in a stream, starting
        from the oldest event and ending with the most recent event.

        :param sleep int: (optional) if provided, sleep this long between polls

        :rtype: CloudWatchLogStreamTailer
        """
        return CloudWatchLogStreamTailer(self, sleep)
        return CloudWatchLogStreamIterator(self, sleep)
