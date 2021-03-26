from datetime import datetime
import time

from deployfish.aws import get_boto3_session


class CloudwatchLogsTailer(object):
    """
    An iterator class that allows you to iterate through your cloudwatch logs from a log stream.
    """

    def __init__(self, group, stream, sleep=5):
        self.client = get_boto3_session().client('logs')
        self.kwargs = {
            'logGroupName': group,
            'logStreamName': stream,
            'startFromHead': True,
            'nextToken': None
        }
        self.sleep = sleep

    def __iter__(self):
        return self

    def __next__(self):
        time.sleep(self.sleep)
        response = self.client.get_log_events(**self.kwargs)
        lines = []
        for event in response['events']:
            timestamp = datetime.utcfromtimestamp(event['timestamp'])
            lines.append('{} {}'.format(
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                event['message']
            ))
        token = response['nextForwardToken']
        if token == self.kwargs['nextToken']:
            raise StopIteration
        self.kwargs['nextToken'] = token
        return lines
