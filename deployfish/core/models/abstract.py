from copy import deepcopy
import json

from botocore import waiter, xform_name
from jsondiff import diff

from deployfish.core.aws import get_boto3_session
from deployfish.core.waiters import create_hooked_waiter_with_client
from deployfish.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ObjectImproperlyConfigured,
    ObjectReadOnly,
    OperationFailed,
)
from deployfish.registry import importer_registry


class LazyAttributeMixin(object):

    def __init__(self):
        self.cache = {}
        super(LazyAttributeMixin, self).__init__()

    def get_cached(self, key, populator, args, kwargs=None):
        kwargs = kwargs if kwargs else {}
        if key not in self.cache:
            self.cache[key] = populator(*args, **kwargs)
        return self.cache[key]

    def purge_cache(self):
        self.cache = {}


class Manager(object):

    service = None

    def __init__(self):
        if self.service:
            self.client = get_boto3_session().client(self.service)
        else:
            self.client = None

    def get(self, pk, **kwargs):
        raise NotImplementedError

    def get_many(self, pk, **kwargs):
        raise NotImplementedError

    def save(self, obj, **kwargs):
        raise NotImplementedError

    def exists(self, pk):
        try:
            self.get(pk)
        except ObjectDoesNotExist:
            return False
        return True

    def list(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, obj, **kwargs):
        raise NotImplementedError

    def diff(self, obj):
        aws_obj = self.get(obj.pk)
        return obj.diff(aws_obj)

    def needs_update(self, obj):
        aws_obj = self.get(obj.pk)
        return obj == aws_obj

    def get_waiter(self, waiter_name):
        config = self.client._get_waiter_config()
        if not config:
            raise ValueError("Waiter does not exist: %s" % waiter_name)
        model = waiter.WaiterModel(config)
        mapping = {}
        for name in model.waiter_names:
            mapping[xform_name(name)] = name
        if waiter_name not in mapping:
            raise ValueError("Waiter does not exist: %s" % waiter_name)
        return create_hooked_waiter_with_client(mapping[waiter_name], model, self.client)


class Model(LazyAttributeMixin):

    objects = None
    adapters = importer_registry
    config_section = None

    class DoesNotExist(ObjectDoesNotExist):
        pass

    class MultipleObjectsReturned(MultipleObjectsReturned):
        pass

    class ImproperlyConfigured(ObjectImproperlyConfigured):
        pass

    class ReadOnly(ObjectReadOnly):
        pass

    class OperationFailed(OperationFailed):
        pass

    @classmethod
    def adapt(cls, obj, source, **kwargs):
        adapter = cls.adapters.get(cls.__name__, source)(obj, **kwargs)
        data, data_kwargs = adapter.convert()
        return data, data_kwargs

    @classmethod
    def new(cls, obj, source, **kwargs):
        data, kwargs = cls.adapt(obj, source, **kwargs)
        return cls(data, **kwargs)

    def __init__(self, data):
        super(Model, self).__init__()
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
    def exists(self):
        return self.objects.exists(self.pk)

    def render_for_display(self):
        return self.render()

    def render_for_diff(self):
        return self.render()

    def render_for_create(self):
        return self.render()

    def render_for_update(self):
        return self.render()

    def render(self):
        data = deepcopy(self.data)
        return data

    def save(self):
        return self.objects.save(self)

    def delete(self):
        self.objects.delete(self)

    def copy(self):
        return self.__class__(self.render_for_create())

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.render_for_diff() == other.render_for_diff()

    def diff(self, other=None):
        if not other:
            other = self.objects.get(self.pk)
        if self.__class__ != other.__class__:
            raise ValueError('{} is not a {}'.format(str(other), self.__class__.__name__))
        return json.loads(diff(other.render_for_diff(), self.render_for_diff(), syntax='explicit', dump=True))

    def reload_from_db(self):
        self.purge_cache()
        new = self.objects.get(self.pk)
        self.data = new.data

    def __str__(self):
        return '{}(pk="{}")'.format(self.__class__.__name__, self.pk)
