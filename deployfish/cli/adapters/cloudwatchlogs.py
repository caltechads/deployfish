from deployfish.core.models import CloudWatchLogGroup, CloudWatchLogStream

from .abstract import ClickModelAdapter
from .commands import ClickTailLogStreamCommandMixin, ClickTailLogGroupCommandMixin


class ClickCloudWatchLogGroupAdapter(
    ClickTailLogGroupCommandMixin,
    ClickModelAdapter
):

    model = CloudWatchLogGroup

    list_ordering = 'Name'
    list_result_columns = {
        'Name': 'logGroupName',
        'Created': {'key': 'creationTime', 'datatype': 'timestamp'},
        'Retention': {'key': 'retentionInDays', 'default': 'inf'},
        'Size': {'key': 'storedBytes', 'datatype': 'bytes'}
    }


class ClickCloudWatchLogStreamAdapter(
    ClickTailLogStreamCommandMixin,
    ClickModelAdapter
):

    model = CloudWatchLogStream

    list_ordering = 'Name'
    list_result_columns = {
        'Name': 'logStreamName',
        'Group': 'logGroupName',
        'Created': {'key': 'creationTime', 'datatype': 'timestamp'},
        'lastEventTimestamp': {'key': 'lastEventTimestamp', 'datatype': 'timestamp', 'default': ''},
    }
