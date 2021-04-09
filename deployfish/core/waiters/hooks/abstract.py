

class AbstractWaiterHook(object):

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, status, response, num_attempts, **kwargs):
        """
        args:
            * 'state': the current state of the waiter. One of 'waiting', 'success', 'failure', 'error' or 'timeout'.
            * 'response': the boto3 response from the last invocation of our waiter's operation
            * 'num_attempts': the current iteration number

        kwargs:

            * 'name': the name of the waiter
            * 'config': the SingleWaiterConfig object passed to the constructor
            * 'WaiterConfig': (optional) not sure
            * 'Delay': (optional) the sleep amount in seconds
            * 'MaxAttempts': (optional) how many iterations we'll perform before timing out

        Plus other waiter specific kwargs.  e.g. Bucket when doing a 'bucket_exists' waiter.
        """
        raise NotImplementedError
