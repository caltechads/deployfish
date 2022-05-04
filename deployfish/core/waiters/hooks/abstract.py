import click


class AbstractWaiterHook:

    def __init__(self, obj):
        self.obj = obj

    def mark(self, status, response, num_attempts, **kwargs):
        click.secho('=' * 72, fg='yellow', bold=True)

    def setup(self, status, response, num_attempts, **kwargs):
        """
        Do any necessary setup on the waiter iteration before we've done our per-state processing.   This will get
        called once per iteration.
        """
        pass

    def waiting(self, status, response, num_attempts, **kwargs):
        """
        Do something when our waiter status is 'waiting'.
        """
        pass

    def success(self, status, response, num_attempts, **kwargs):
        """
        Do something when our waiter status is 'success'.
        """
        pass

    def failure(self, status, response, num_attempts, **kwargs):
        """
        Do something when our waiter status is 'failure'.
        """
        pass

    def error(self, status, response, num_attempts, **kwargs):
        """
        Do something when our waiter status is 'error'.
        """
        pass

    def timeout(self, status, response, num_attempts, **kwargs):
        """
        Do something when our waiter status is 'timeout'.
        """
        pass

    def cleanup(self, status, response, num_attempts, **kwargs):
        """
        Do any necessary cleanup after the waiter iteration has completed and we've done our per-state processing.
        This will get called once per iteration.
        """
        pass

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
        self.setup(status, response, num_attempts, **kwargs)
        if status == 'waiting':
            self.waiting(status, response, num_attempts, **kwargs)
        elif status == 'success':
            self.success(status, response, num_attempts, **kwargs)
        elif status == 'failure':
            self.failure(status, response, num_attempts, **kwargs)
        elif status == 'error':
            self.failure(status, response, num_attempts, **kwargs)
        elif status == 'timeout':
            self.failure(status, response, num_attempts, **kwargs)
        self.cleanup(status, response, num_attempts, **kwargs)
