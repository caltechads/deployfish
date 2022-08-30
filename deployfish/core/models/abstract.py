from copy import deepcopy
import json
from typing import Callable, List, Any, Dict, Sequence, Union, NoReturn

from botocore import waiter, xform_name
from jsondiff import diff

from deployfish.types import SupportsCache, SupportsModel
from deployfish.core.aws import get_boto3_session
from deployfish.core.waiters import create_hooked_waiter_with_client
from deployfish.exceptions import (
    MultipleObjectsReturned as BaseMultipleObjectsReturned,
    ObjectDoesNotExist,
    ObjectImproperlyConfigured,
    ObjectReadOnly,
    OperationFailed as BaseOperationFailed,
)
from deployfish.registry import importer_registry


class LazyAttributeMixin(SupportsCache):

    def __init__(self) -> None:
        self.cache: Dict[str, Any] = {}
        super().__init__()

    def get_cached(self, key: str, populator: Callable, args: List[Any], kwargs: Dict[str, Any] = None) -> Any:
        kwargs = kwargs if kwargs else {}
        if key not in self.cache:
            self.cache[key] = populator(*args, **kwargs)
        return self.cache[key]

    def purge_cache(self) -> None:
        self.cache = {}


class Manager:

    service: str

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self.service:
            self._client = get_boto3_session().client(self.service)
        else:
            self._client = None
        return self._client

    def get(self, pk: str, **_) -> "Model":
        raise NotImplementedError

    def get_many(self, pks: List[str], **_) -> Sequence["Model"]:
        raise NotImplementedError

    def save(self, obj: "Model", **_) -> Any:
        raise obj.ReadOnly(f'Cannot modify {obj.__class__.__name__} objects with deployfish.')

    def exists(self, pk: str) -> bool:
        try:
            self.get(pk)
        except ObjectDoesNotExist:
            return False
        return True

    list: Callable[..., Sequence["Model"]]

    def delete(self, obj: "Model", **_) -> Union[None, NoReturn]:
        raise obj.ReadOnly(f'Cannot modify {obj.__class__.__name__} objects with deployfish.')

    def diff(self, obj: "Model") -> Dict[str, Any]:
        aws_obj = self.get(obj.pk)
        return obj.diff(aws_obj)

    def needs_update(self, obj: "Model") -> bool:
        aws_obj = self.get(obj.pk)
        return obj == aws_obj

    def get_waiter(self, waiter_name: str):
        config = self.client._get_waiter_config()  # pylint:disable=protected-access
        if not config:
            raise ValueError("Waiter does not exist: %s" % waiter_name)
        model = waiter.WaiterModel(config)
        mapping = {}
        for name in model.waiter_names:
            mapping[xform_name(name)] = name
        if waiter_name not in mapping:
            raise ValueError("Waiter does not exist: %s" % waiter_name)
        return create_hooked_waiter_with_client(mapping[waiter_name], model, self.client)


class Model(LazyAttributeMixin, SupportsModel):

    objects: Manager
    adapters = importer_registry
    config_section: str = 'NO_SECTION'

    class DoesNotExist(ObjectDoesNotExist):
        """
        We tried to get a single object but it does not exist in AWS.
        """
        pass

    class MultipleObjectsReturned(BaseMultipleObjectsReturned):
        """
        We expected to retrieve only one object but got multiple objects.
        """
        pass

    class ImproperlyConfigured(ObjectImproperlyConfigured):
        """
        Deployfish, our Manager or the model itself is not properly configured.
        """
        pass

    class ReadOnly(ObjectReadOnly):
        """
        This is a read only model; no writes to AWS permitted.
        """
        pass

    class OperationFailed(BaseOperationFailed):
        """
        We did a call to AWS we expected to succeed, but it failed.
        """
        pass

    @classmethod
    def adapt(cls, obj: Dict[str, Any], source: str, **kwargs):
        """
        Given an appropriate bit of data `obj` from a data source `source`, return the appropriate args and kwargs to to
        the Model.new factory method so it can use them to construct the model instance.  This means:  take the
        data in `obj` and convert it to look like the dict returned by AWS when we use boto3 to retrieve a single object
        of this type.

        .. note::

            At this time, the only valid `source` is `deployfish`, and so all `obj` will be bits of parsed
            deployfish.yml data.  CPM 2021-09
        """
        adapter = cls.adapters.get(cls.__name__, source)(obj, **kwargs)
        data, data_kwargs = adapter.convert()
        return data, data_kwargs

    @classmethod
    def new(cls, obj: Dict[str, Any], source: str, **kwargs) -> "Model":
        """
        This is a factory method.

        .. note::

            The ``**kwargs`` here is for the Adapter to use, not for the Model constructor.  So don't be confused if
            kwargs are passed in here which do not get used on the model.
        """
        data, model_kwargs = cls.adapt(obj, source, **kwargs)
        return cls(data, **model_kwargs)

    def __init__(self, data):
        super().__init__()
        self.data = data

    @property
    def pk(self):
        raise NotImplementedError

    @property
    def name(self):
        raise NotImplementedError

    @property
    def arn(self):
        raise NotImplementedError

    @property
    def exists(self) -> bool:
        return self.objects.exists(self.pk)

    def render_for_display(self) -> Dict[str, Any]:
        return self.render()

    def render_for_diff(self) -> Dict[str, Any]:
        return self.render()

    def render_for_create(self) -> Dict[str, Any]:
        return self.render()

    def render_for_update(self) -> Dict[str, Any]:
        return self.render()

    def render(self) -> Dict[str, Any]:
        data = deepcopy(self.data)
        return data

    def save(self):
        return self.objects.save(self)

    def delete(self) -> None:
        self.objects.delete(self)

    def copy(self) -> "Model":
        return self.__class__(self.render_for_create())

    def __eq__(self, other) -> bool:
        if self.__class__ != other.__class__:
            return False
        return self.render_for_diff() == other.render_for_diff()

    def diff(self, other=None) -> Dict[str, Any]:
        if not other:
            other = self.objects.get(self.pk)
        if self.__class__ != other.__class__:
            raise ValueError(f'{str(other)} is not a {self.__class__.__name__}')
        return json.loads(diff(other.render_for_diff(), self.render_for_diff(), syntax='explicit', dump=True))

    def reload_from_db(self) -> None:
        self.purge_cache()
        new = self.objects.get(self.pk)
        self.data = new.data

    def __str__(self) -> str:
        return '{}(pk="{}")'.format(self.__class__.__name__, self.pk)
