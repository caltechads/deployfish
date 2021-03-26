from copy import copy

from jsondiff import diff

from deployfish.aws import get_boto3_session
from deployfish.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ObjectImproperlyConfigured,
    ObjectReadOnly,
    OperationalError,
)
from deployfish.adapters import registry


class Manager(object):

    service = None

    def __init__(self):
        self.client = get_boto3_session().client(self.service)

    def get(self, pk, **kwargs):
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


class Model(object):

    objects = None
    adapters = registry

    class DoesNotExist(ObjectDoesNotExist):
        pass

    class MultipleObjectsReturned(MultipleObjectsReturned):
        pass

    class ImproperlyConfigured(ObjectImproperlyConfigured):
        pass

    class ReadOnly(ObjectReadOnly):
        pass

    class OperationalError(OperationalError):
        pass

    @classmethod
    def adapt(cls, obj, source, **kwargs):
        adapter = cls.adapters.get(cls.__name__, source)(obj, **kwargs)
        data, kwargs = adapter(obj, **kwargs).convert()
        return data, kwargs

    @classmethod
    def new(cls, obj, source, **kwargs):
        data, kwargs = cls.adapt(obj, source, **kwargs)
        return cls(data, **kwargs)

    def __init__(self, data, **kwargs):
        self.data = data
        self.cache = {}

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

    def render_for_diff(self):
        return self.render()

    def render_for_create(self):
        return self.render()

    def render_for_update(self):
        return self.render()

    def render(self):
        data = copy(self.data)
        return data

    def save(self):
        self.objects.save(self)

    def delete(self):
        self.objects.delete(self)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return self.render_for_diff() == other.render_for_diff()

    def diff(self, other):
        if self.__class__ != other.__class__:
            raise ValueError('{} is not a {)'.format(str(other), self.__class__.__name__))
        return diff(self.render_for_diff(), other.render_for_diff())

    def get_cached(self, key, populator, args, kwargs=None):
        kwargs = kwargs if kwargs else {}
        if key not in self.cache:
            self.cache[key] = populator(*args, **kwargs)
        return self.cache[key]

    def reload_from_db(self):
        self.cache = {}
        new = self.objects.get(self.pk)
        self.data = new.data

    def __str__(self):
        return '{}(pk="{}")'.format(self.__class__.__name__, self.pk)
