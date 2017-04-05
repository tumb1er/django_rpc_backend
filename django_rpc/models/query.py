# coding: utf-8
import functools
from collections import namedtuple
from datetime import datetime

import pytz

from django_rpc.celery.client import RpcClient
from django_rpc.models import utils

Trace = namedtuple('Trace', ('method', 'args', 'kwargs'))


def dict_filter(d, keys):
    return {k: v for k, v in d.items() if k in keys}


class BaseIterable(object):
    def __init__(self, queryset):
        """
        :type queryset: RpcBaseQuerySet 
        """
        self.queryset = queryset

    def __iter__(self):
        result = self.queryset.fetch()
        for item in result:
            yield self.queryset.instantiate(item)


class EmptyIterable(BaseIterable):
    def __iter__(self):
        return iter([])


class ValuesIterable(BaseIterable):
    def __iter__(self):
        result = self.queryset.fetch()
        return iter(result)


class DateTimeIterable(BaseIterable):

    def __init__(self, queryset, tzinfo=pytz.utc):
        super().__init__(queryset)
        # FIXME: tzinfo support may be different for different server databases
        # https://docs.djangoproject.com/en/1.10/ref/models/querysets/#datetimes
        self.tzinfo = tzinfo

    def __iter__(self):
        result = self.queryset.fetch()
        for item in result:
            # parse naive
            dt = datetime.strptime(item, '%Y-%m-%dT%H:%M:%SZ')
            # cast to utc
            dt = datetime(*dt.timetuple()[:6], tzinfo=pytz.utc)
            # move to local tz
            yield dt.astimezone(self.tzinfo)


# noinspection PyPep8Naming
def TZDateTimeIterable(tzinfo):
    return functools.partial(DateTimeIterable, tzinfo=tzinfo)


class DateIterable(BaseIterable):
    def __iter__(self):
        result = self.queryset.fetch()
        for item in result:
            yield datetime.strptime(item, '%Y-%m-%d').date()


class RpcBaseQuerySet(object):
    """ Django-style реализация конфигуратора запроса к rpc."""

    _rpc_cloned = [
        '_return_native',
        '_field_list',
        '_extra_fields',
        '_related_fields',
        '_exclude_fields',
        '_iterable_class'
    ]

    _iterable_class = BaseIterable

    def __init__(self, model):
        self.model = model
        self._result_cache = None
        self.__trace = ()
        self.__field_list = ()
        self._extra_fields = ()  # qs.extra()
        self._exclude_fields = ()  # qs.defer(), qs.only()
        self._related_fields = ()  # qs.select_related()
        self._prefetch_fields = ()  # qs.prefetch_related()
        self._return_native = False
        super(RpcBaseQuerySet, self).__init__()

    def _trace(self, method, args, kwargs, iterable=None):
        clone = self._clone()
        new_trace = Trace(method, args, kwargs)
        # noinspection PyTypeChecker
        clone.__trace = self.__trace + (new_trace,)
        if iterable:
            clone._iterable_class = iterable
        return clone

    def _clone(self):
        clone = self.__class__(model=self.model)
        for f in self._rpc_cloned:
            setattr(clone, f, getattr(self, f))
        return clone

    @property
    def rpc_trace(self):
        return self.__trace

    @property
    def _field_list(self):
        return self.__field_list

    @_field_list.setter
    def _field_list(self, value):
        value = tuple(value)
        pk_name = self._get_pk_field()
        if value and pk_name not in value:
            value += (pk_name,)
        self.__field_list = value

    def iterator(self):
        return iter(self._iterable_class(self))

    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = list(self.iterator())

    def __iter__(self):
        self._fetch_all()
        return iter(self._result_cache)

    def instantiate(self, data):
        obj = self.model()
        self.update_model(obj, data)
        for f in self._exclude_fields:
            if hasattr(obj, f):
                delattr(obj, f)
        if self._field_list:
            for k in list(obj.__dict__.keys()):
                if k not in self._field_list:
                    delattr(obj, k)
        return obj

    def fetch(self):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        extra_fields = (self._extra_fields + self._related_fields +
                        self._prefetch_fields)
        result = client.fetch(opts.app_label, opts.name, self.__trace,
                              fields=self._field_list or None,
                              extra_fields=extra_fields,
                              exclude_fields=self._exclude_fields,
                              native=self._return_native)
        return result

    def annotate(self, *args, **kwargs):
        kw = {expr: expr.default_alias for expr in args}
        kw.update(kwargs)
        qs = self._trace('annotate', args, kwargs)
        qs._extra_fields += tuple(kw.keys())
        return qs

    def select_related(self, *args, **kwargs):
        qs = self._trace('select_related', args, kwargs)
        if args and args[0] is None:
            qs._related_fields = ()
        else:
            qs._related_fields += tuple(args)
        return qs

    def prefetch_related(self, *args, **kwargs):
        qs = self._trace('prefetch_related', args, kwargs)
        if args and args[0] is None:
            qs._prefetch_fields = ()
        else:
            qs._prefetch_fields += tuple(args)
        return qs

    def extra(self, *args, **kwargs):
        qs = self._trace('extra', args, kwargs)
        select = kwargs.get('select')
        if select:
            qs._extra_fields = tuple(select.keys())
        return qs

    def defer(self, *args, **kwargs):
        qs = self._trace('defer', args, kwargs)
        if args == (None,):
            qs._exclude_fields = ()
        else:
            qs._exclude_fields += tuple(args)
        return qs

    def only(self, *args, **kwargs):
        qs = self._trace('only', args, kwargs)
        if qs._exclude_fields:
            # This is how django-1.10 works: if query.defer is not empty,
            # django removes deferred fields from "only-fields"
            qs._exclude_fields = [f for f in qs._exclude_fields
                                  if f not in args]
        else:
            qs._field_list = args
        return qs

    def update(self, *args, **kwargs):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        assert not args, "args not supported for update"
        data = kwargs
        result = client.update(opts.app_label, opts.name, self.rpc_trace, data)
        return result

    def delete(self, *args, **kwargs):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        assert not args, "args not supported for delete"
        assert not kwargs, "kwargs not supported for delete"
        result = client.delete(opts.app_label, opts.name, self.rpc_trace)
        return result

    def bulk_create(self, objects, batch_size=None):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        fields = self._get_fields(objects[0])

        total = len(objects)
        batch_size = batch_size or total
        offset = 0
        inserted = []
        while offset < total:
            inserting = objects[offset: offset + batch_size]
            data = [dict_filter(obj.__dict__, fields)
                    for obj in inserting]
            results = client.insert(opts.app_label, opts.name, data, fields)
            for obj, res in zip(inserting, results):
                self.update_model(obj, res)
            inserted.extend(inserting)
            offset += batch_size
        return inserted

    # noinspection PyMethodMayBeStatic
    def update_model(self, obj, data):
        model = type(obj)
        for k, v in data.items():
            try:
                descriptor = getattr(model, k)
                descriptor.set(obj, v)
            except AttributeError:
                setattr(obj, k, v)

    def get_or_create(self, *args, **kwargs):
        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        assert not args, "args not supported for create"
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, kwargs)
        instance = self.instantiate(data)

        return instance, created

    def update_or_create(self, *args, **kwargs):
        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        assert not args, "args not supported for create"
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, kwargs, update=True)
        instance = self.instantiate(data)

        return instance, created

    @staticmethod
    def _get_fields(obj):
        return list(obj.__dict__.keys())

    def _get_pk_field(self):
        return self.model.Rpc.pk_field

    def datetimes(self, *args, **kwargs):
        tzinfo = kwargs.pop('tzinfo', pytz.utc)
        qs = self._trace('datetimes', args, kwargs,
                         iterable=TZDateTimeIterable(tzinfo))
        qs._return_native = True
        return qs

    # noinspection PyUnusedLocal
    def in_bulk(self, *args, **kwargs):
        objects = list(self.iterator())
        pk_name = self._get_pk_field()
        return {getattr(obj, pk_name): obj for obj in objects}

    # noinspection PyUnusedLocal
    def as_manager(self, *args, **kwargs):
        base_manager = type(self.model.objects)
        manager_class = type("ManagerFromQuerySet",
                             (base_manager,),
                             {'_queryset_class': type(self)})
        return manager_class()


class RpcQuerySet(RpcBaseQuerySet):
    """
    Official Django QuerySet API
    @see https://docs.djangoproject.com/en/1.10/ref/models/querysets/
    
    """

    #
    # methods-that-return-new-querysets
    #

    @utils.queryset_method
    def filter(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.queryset_method
    def exclude(self, *args, **kwargs):
        pass  # pragma: nocover

    annotate = RpcBaseQuerySet.annotate

    @utils.queryset_method
    def order_by(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.queryset_method
    def reverse(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.queryset_method
    def distinct(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.values_queryset_method(ValuesIterable)
    def values(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.values_queryset_method(ValuesIterable)
    def values_list(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.values_queryset_method(DateIterable)
    def dates(self, *args, **kwargs):
        pass  # pragma: nocover

    datetimes = RpcBaseQuerySet.datetimes

    @utils.values_queryset_method(EmptyIterable)
    def none(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.queryset_method
    def all(self, *args, **kwargs):
        pass  # pragma: nocover

    select_related = RpcBaseQuerySet.select_related

    prefetch_related = RpcBaseQuerySet.prefetch_related

    extra = RpcBaseQuerySet.extra

    defer = RpcBaseQuerySet.defer

    only = RpcBaseQuerySet.only

    def using(self, *args, **kwargs):
        # database change is an rpc server responsibility
        raise NotImplementedError()

    def select_for_update(self, *args, **kwargs):
        # transaction management is an rpc server responsibility
        raise NotImplementedError()

    def raw(self, *args, **kwargs):
        # performing sql queries is an rpc server responsibility
        raise NotImplementedError()

    #
    # methods-that-do-not-return-querysets
    #

    @utils.single_object_method
    def get(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.single_object_method
    def create(self, *args, **kwargs):
        pass  # pragma: nocover

    get_or_create = RpcBaseQuerySet.get_or_create

    update_or_create = RpcBaseQuerySet.update_or_create

    bulk_create = RpcBaseQuerySet.bulk_create

    @utils.value_method
    def count(self, *args, **kwargs):
        pass  # pragma: nocover

    in_bulk = RpcBaseQuerySet.in_bulk

    iterator = RpcBaseQuerySet.iterator

    @utils.single_object_method
    def latest(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.single_object_method
    def earliest(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.single_object_method
    def first(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.single_object_method
    def last(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.value_method
    def aggregate(self, *args, **kwargs):
        pass  # pragma: nocover

    @utils.value_method
    def exists(self, *args, **kwargs):
        pass  # pragma: nocover

    update = RpcBaseQuerySet.update

    delete = RpcBaseQuerySet.delete

    as_manager = RpcBaseQuerySet.as_manager
