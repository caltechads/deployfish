from copy import copy
import logging
import time

from botocore.utils import get_service_module_name
from botocore.docs.docstring import WaiterDocstring
from botocore import xform_name
from botocore.waiter import NormalizedOperationMethod

from botocore.exceptions import WaiterError


logger = logging.getLogger(__name__)


def create_hooked_waiter_with_client(waiter_name, waiter_model, client):
    """

    :type waiter_name: str
    :param waiter_name: The name of the waiter.  The name should match
        the name (including the casing) of the key name in the waiter
        model file (typically this is CamelCasing).

    :type waiter_model: botocore.waiter.WaiterModel
    :param waiter_model: The model for the waiter configuration.

    :type client: botocore.client.BaseClient
    :param client: The botocore client associated with the service.

    :rtype: botocore.waiter.Waiter
    :return: The waiter object.

    """
    single_waiter_config = waiter_model.get_waiter(waiter_name)
    operation_name = xform_name(single_waiter_config.operation)
    operation_method = NormalizedOperationMethod(
        getattr(client, operation_name))

    # Create a new wait method that will serve as a proxy to the underlying
    # Waiter.wait method. This is needed to attach a docstring to the
    # method.
    def wait(self, **kwargs):
        HookedWaiter.wait(self, **kwargs)

    wait.__doc__ = WaiterDocstring(
        waiter_name=waiter_name,
        event_emitter=client.meta.events,
        service_model=client.meta.service_model,
        service_waiter_model=waiter_model,
        include_signature=False
    )

    # Rename the waiter class based on the type of waiter.
    waiter_class_name = str('%s.HookedWaiter.%s' % (
        get_service_module_name(client.meta.service_model),
        waiter_name))

    # Create the new waiter class
    documented_waiter_cls = type(
        waiter_class_name, (HookedWaiter,), {'wait': wait})

    # Return an instance of the new waiter class.
    return documented_waiter_cls(
        waiter_name, single_waiter_config, operation_method
    )


class HookedWaiter(object):
    """

    A HookedWaiter is almost exactly like a standard boto3 Waiter with one difference:
    you can give it a list of callables that will be executed on each iteration.  This
    is useful for many things like giving user feedback while we're waiting.

    To use hooks on each iteration of our waiting, pass a kwarg named `WaiterHooks`
    to waiter.wait().

    `WaiterHooks` is should be a list of callables with this prototype:

        waiter_hook(state, response, num_attempts, **kwargs)

    Where:

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
    def __init__(self, name, config, operation_method):
        """

        :type name: string
        :param name: The name of the waiter

        :type config: botocore.waiter.SingleWaiterConfig
        :param config: The configuration for the waiter.

        :type operation_method: callable
        :param operation_method: A callable that accepts **kwargs
            and returns a response.  For example, this can be
            a method from a botocore client.

        """
        self._operation_method = operation_method
        # The two attributes are exposed to allow for introspection
        # and documentation.
        self.name = name
        self.config = config

    def wait(self, **kwargs):
        hook_kwargs = copy(kwargs)
        acceptors = list(self.config.acceptors)
        current_state = 'waiting'
        # pop the invocation specific config
        config = kwargs.pop('WaiterConfig', {})
        hooks = kwargs.pop('WaiterHooks', [])
        sleep_amount = config.get('Delay', self.config.delay)
        max_attempts = config.get('MaxAttempts', self.config.max_attempts)
        # ------------------------------
        # Build our hook kwargs
        # ------------------------------
        hook_kwargs['name'] = self.name
        hook_kwargs['config'] = self.config
        if 'WaiterHooks' in hook_kwargs:
            del hook_kwargs['WaiterHooks']
        if 'MaxAttempts' not in hook_kwargs:
            hook_kwargs['MaxAttempts'] = max_attempts
        if 'Delay' not in hook_kwargs:
            hook_kwargs['Delay'] = sleep_amount
        # ------------------------------
        last_matched_acceptor = None
        num_attempts = 0

        while True:
            response = self._operation_method(**kwargs)
            num_attempts += 1
            for acceptor in acceptors:
                if acceptor.matcher_func(response):
                    last_matched_acceptor = acceptor
                    current_state = acceptor.state
                    break
            else:
                # If none of the acceptors matched, we should
                # transition to the failure state if an error
                # response was received.
                if 'Error' in response:
                    # ----------------------------------------
                    # Error hook invocation
                    # ----------------------------------------
                    hook_kwargs['state'] = 'error'
                    for hook in hooks:
                        hook('error', response, num_attempts, **hook_kwargs)
                    # ----------------------------------------
                    # Transition to a failure state, which we
                    # can just handle here by raising an exception.
                    raise WaiterError(
                        name=self.name,
                        reason='An error occurred (%s): %s' % (
                            response['Error'].get('Code', 'Unknown'),
                            response['Error'].get('Message', 'Unknown'),
                        ),
                        last_response=response,
                    )
            # ----------------------------------------
            # Normal hook invocation
            # ----------------------------------------
            for hook in hooks:
                hook(current_state, response, num_attempts, **kwargs)
            # ----------------------------------------
            if current_state == 'success':
                logger.debug("Waiting complete, waiter matched the "
                             "success state.")
                return
            if current_state == 'failure':
                reason = 'Waiter encountered a terminal failure state: %s' % (
                    acceptor.explanation
                )
                raise WaiterError(
                    name=self.name,
                    reason=reason,
                    last_response=response,
                )
            if num_attempts >= max_attempts:
                # ----------------------------------------
                # Timeout hook invocation
                # ----------------------------------------
                for hook in hooks:
                    hook('timeout', response, num_attempts, **kwargs)
                # ----------------------------------------
                if last_matched_acceptor is None:
                    reason = 'Max attempts exceeded'
                else:
                    reason = 'Max attempts exceeded. Previously accepted state: %s' % (
                        acceptor.explanation
                    )
                raise WaiterError(
                    name=self.name,
                    reason=reason,
                    last_response=response,
                )
            time.sleep(sleep_amount)
