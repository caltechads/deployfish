import json
from collections.abc import Callable, Sequence
from copy import deepcopy
from typing import Any

from botocore import waiter, xform_name
from jsondiff import diff

from deployfish.core.aws import get_boto3_session
from deployfish.core.waiters import create_hooked_waiter_with_client
from deployfish.exceptions import (
    MultipleObjectsReturned as BaseMultipleObjectsReturned,
)
from deployfish.exceptions import (
    ObjectDoesNotExist,
    ObjectImproperlyConfigured,
    ObjectReadOnly,
)
from deployfish.exceptions import (
    OperationFailed as BaseOperationFailed,
)
from deployfish.registry import importer_registry
from deployfish.types import SupportsCache, SupportsModel


class LazyAttributeMixin(SupportsCache):
    """
    Model lazy attribute mixin behavior.
    """

    def __init__(self) -> None:
        #: Cache.
        """
        Initialize LazyAttributeMixin.
        """
        #: Cache.
        self.cache: dict[str, Any] = {}
        super().__init__()

    def get_cached(
        self,
        key: str,
        populator: Callable,
        args: list[Any],
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """
        Get cached.

        Args:
            key: key.
            populator: populator.
            args: args.
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        kwargs = kwargs or {}
        if key not in self.cache:
            self.cache[key] = populator(*args, **kwargs)
        return self.cache[key]

    def purge_cache(self) -> None:
        """
        Purge cache.
        """
        self.cache = {}


class Manager:
    """
    Model manager behavior.
    """

    #: Service.
    service: str

    def __init__(self):
        #: Client.
        """
        Initialize Manager.
        """
        #: Client.
        self._client = None

    @property
    def client(self):
        """
        Client.

        Returns:
            Operation result.

        """
        if self.service:
            self._client = get_boto3_session().client(self.service)
        else:
            self._client = None
        return self._client

    def get(self, pk: str, **_) -> "Model":
        """
        Get.

        Args:
            pk: pk.

        Keyword Args:
            _: .

        """
        raise NotImplementedError

    def get_many(self, pks: list[str], **_) -> Sequence["Model"]:
        """
        Get many.

        Args:
            pks: pks.

        Keyword Args:
            _: .

        """
        raise NotImplementedError

    def save(self, obj: "Model", **_) -> Any:
        """
        Save.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        """
        msg = f"Cannot modify {obj.__class__.__name__} objects with deployfish."
        raise obj.ReadOnly(msg)

    def exists(self, pk: str) -> bool:
        """
        Exists.

        Args:
            pk: pk.

        Returns:
            Operation result.

        """
        try:
            self.get(pk)
        except ObjectDoesNotExist:
            return False
        return True

    #: List.
    list: Callable[..., Sequence["Model"]]

    def delete(self, obj: "Model", **_) -> None:
        """
        Delete.

        Args:
            obj: obj.

        Keyword Args:
            _: .

        """
        msg = f"Cannot modify {obj.__class__.__name__} objects with deployfish."
        raise obj.ReadOnly(msg)

    def diff(self, obj: "Model") -> dict[str, Any]:
        """
        Diff.

        Args:
            obj: obj.

        Returns:
            Operation result.

        """
        aws_obj = self.get(obj.pk)
        return obj.diff(aws_obj)

    def needs_update(self, obj: "Model") -> bool:
        """
        Needs update.

        Args:
            obj: obj.

        Returns:
            Operation result.

        """
        aws_obj = self.get(obj.pk)
        return obj == aws_obj

    def get_waiter(self, waiter_name: str):
        """
        Get waiter.

        Args:
            waiter_name: waiter name.

        Returns:
            Operation result.

        """
        config = self.client._get_waiter_config()  # pylint:disable=protected-access
        if not config:
            msg = f"Waiter does not exist: {waiter_name}"
            raise ValueError(msg)
        model = waiter.WaiterModel(config)
        mapping = {}
        for name in model.waiter_names:
            mapping[xform_name(name)] = name
        if waiter_name not in mapping:
            msg = f"Waiter does not exist: {waiter_name}"
            raise ValueError(msg)
        return create_hooked_waiter_with_client(
            mapping[waiter_name], model, self.client
        )


class Model(LazyAttributeMixin, SupportsModel):  # noqa: PLW1641
    """
    Model model behavior.

    Args:
        data: data.

    """

    #: Objects.
    objects: Manager
    #: Adapters.
    adapters = importer_registry
    #: Config section.
    config_section: str = "NO_SECTION"

    class DoesNotExist(ObjectDoesNotExist):
        """
        We tried to get a single object but it does not exist in AWS.
        """

    class MultipleObjectsReturned(BaseMultipleObjectsReturned):
        """
        We expected to retrieve only one object but got multiple objects.
        """

    class ImproperlyConfigured(ObjectImproperlyConfigured):
        """
        Deployfish, our Manager or the model itself is not properly configured.
        """

    class ReadOnly(ObjectReadOnly):
        """

        is a read only model; no writes to AWS permitted.
        """

    class OperationFailed(BaseOperationFailed):
        """
        We did a call to AWS we expected to succeed, but it failed.
        """

    @classmethod
    def adapt(cls, obj: dict[str, Any], source: str, **kwargs):
        """
        Given an appropriate bit of data `obj` from a data source `source`, return the
        appropriate args and kwargs to to
        the Model.new factory method so it can use them to construct the model instance.
        This means:  take the
        data in `obj` and convert it to look like the dict returned by AWS when we use
        boto3 to retrieve a single object
        of this type.

        .. note::

            At this time, the only valid `source` is `deployfish`, and so all `obj` will
            be bits of parsed
            deployfish.yml data.  CPM 2021-09

        Args:
            obj: obj.
            source: source.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        adapter = cls.adapters.get(cls.__name__, source)(obj, **kwargs)
        data, data_kwargs = adapter.convert()
        return data, data_kwargs

    @classmethod
    def new(cls, obj: dict[str, Any], source: str, **kwargs) -> "Model":
        """

        Is a factory method.

        .. note::

            The ``**kwargs`` here is for the Adapter to use, not for the Model
            constructor.  So don't be confused if
            kwargs are passed in here which do not get used on the model.

        Args:
            obj: obj.
            source: source.

        Keyword Args:
            kwargs: kwargs.

        Returns:
            Operation result.

        """
        data, model_kwargs = cls.adapt(obj, source, **kwargs)
        return cls(data, **model_kwargs)

    def __init__(self, data):
        """
        Initialize Model.

        Args:
            data: data.

        """
        super().__init__()
        #: Data.
        self.data = data

    @property
    def pk(self):
        """
        Pk.
        """
        raise NotImplementedError

    @property
    def name(self):
        """
        Name.
        """
        raise NotImplementedError

    @property
    def arn(self):
        """
        Arn.
        """
        raise NotImplementedError

    @property
    def exists(self) -> bool:
        """
        Exists.

        Returns:
            Operation result.

        """
        return self.objects.exists(self.pk)

    def render_for_display(self) -> dict[str, Any]:
        """
        Render for display.

        Returns:
            Operation result.

        """
        return self.render()

    def render_for_diff(self) -> dict[str, Any]:
        """
        Render for diff.

        Returns:
            Operation result.

        """
        return self.render()

    def render_for_create(self) -> dict[str, Any]:
        """
        Render for create.

        Returns:
            Operation result.

        """
        return self.render()

    def render_for_update(self) -> dict[str, Any]:
        """
        Render for update.

        Returns:
            Operation result.

        """
        return self.render()

    def render(self) -> dict[str, Any]:
        """
        Render.

        Returns:
            Operation result.

        """
        return deepcopy(self.data)

    def save(self):
        """
        Save.

        Returns:
            Operation result.

        """
        return self.objects.save(self)

    def delete(self) -> None:
        """
        Delete.
        """
        self.objects.delete(self)

    def copy(self) -> "Model":
        """
        Copy.

        Returns:
            Operation result.

        """
        return self.__class__(self.render_for_create())

    def __eq__(self, other) -> bool:
        """
        Handle eq.

        Args:
            other: other.

        Returns:
            Operation result.

        """
        if self.__class__ != other.__class__:
            return False
        return self.render_for_diff() == other.render_for_diff()

    def diff(self, other=None) -> dict[str, Any]:
        """
        Diff.

        Args:
            other: other.

        Returns:
            Operation result.

        """
        if not other:
            other = self.objects.get(self.pk)
        if self.__class__ != other.__class__:
            msg = f"{other!s} is not a {self.__class__.__name__}"
            raise ValueError(msg)
        return json.loads(
            diff(
                other.render_for_diff(),
                self.render_for_diff(),
                syntax="explicit",
                dump=True,
            )
        )

    def reload_from_db(self) -> None:
        """
        Reload from db.
        """
        self.purge_cache()
        new = self.objects.get(self.pk)
        self.data = new.data

    def __str__(self) -> str:
        """
        Handle str.

        Returns:
            Operation result.

        """
        return f'{self.__class__.__name__}(pk="{self.pk}")'
