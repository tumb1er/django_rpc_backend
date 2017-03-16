# coding: utf-8
from collections import namedtuple

from django_rpc.celery.client import RpcClient
from django_rpc.models import utils


Trace = namedtuple('Trace', ('method', 'args', 'kwargs'))


class RpcBaseQuerySet(object):
    """ Django-style реализация конфигуратора запроса к rpc."""

    _rpc_cloned = [
        '_return_native',
        '_field_list',
        '_extra_fields',
        '_exclude_fields'
    ]

    def __init__(self, model):
        self.model = model
        self.__trace = ()
        self.__field_list = ()
        self._extra_fields = ()
        self._exclude_fields = ()
        self._return_native = False
        super(RpcBaseQuerySet, self).__init__()

    def _trace(self, method, args, kwargs):
        clone = self._clone()
        new_trace = Trace(method, args, kwargs)
        # noinspection PyTypeChecker
        clone.__trace = self.__trace + (new_trace,)
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

    def __iter__(self):
        result = self._fetch()

        for item in result.__iter__():
            if self._return_native:
                yield item
                continue
            obj = self.model()
            obj.__dict__.update(item)
            for f in self._exclude_fields:
                if hasattr(obj, f):
                    delattr(obj, f)
            if self._field_list:
                for k in list(obj.__dict__.keys()):
                    if k not in self._field_list:
                        delattr(obj, k)
            yield obj

    def _fetch(self):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        result = client.fetch(opts.app_label, opts.name, self.__trace,
                              fields=self._field_list or None,
                              extra_fields=self._extra_fields,
                              exclude_fields=self._exclude_fields,
                              native=self._return_native)
        return result

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

    def create(self, *args, **kwargs):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        assert not args, "args not supported for create"
        fields = list(kwargs.keys())
        data = [kwargs]
        result = client.insert(opts.app_label, opts.name, data, fields,
                               return_id=True)
        return result

    def bulk_create(self, objs, batch_size=None):
        # FIXME: batch_size support
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        data = [obj.__dict__ for obj in objs]
        fields = self._get_fields(objs[0])
        client.insert(opts.app_label, opts.name, data, fields)
        return objs

    def get_or_create(self, *args, **kwargs):
        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        assert not args, "args not supported for create"
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, kwargs)
        instance = self.model()
        instance.__dict__.update(data)

        return instance, created

    def update_or_create(self, *args, **kwargs):
        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        assert not args, "args not supported for create"
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, kwargs, update=True)
        instance = self.model()
        instance.__dict__.update(data)

        return instance, created

    @staticmethod
    def _get_fields(obj):
        return list(obj.__dict__.keys())

    def _get_pk_field(self):
        return self.model.Rpc.pk_field


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
        pass

    @utils.queryset_method
    def exclude(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def annotate(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def order_by(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def reverse(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def distinct(self, *args, **kwargs):
        pass

    @utils.values_queryset_method
    def values(self, *args, **kwargs):
        pass

    @utils.values_queryset_method
    def values_list(self, *args, **kwargs):
        pass

    @utils.values_queryset_method
    def dates(self, *args, **kwargs):
        pass

    @utils.values_queryset_method
    def datetimes(self, *args, **kwargs):
        pass

    def none(self, *args, **kwargs):
        """ useless """
        raise NotImplementedError()

    @utils.queryset_method
    def all(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def select_related(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def prefetch_related(self, *args, **kwargs):
        pass

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
        pass

    @utils.single_object_method
    def create(self, *args, **kwargs):
        pass

    get_or_create = RpcBaseQuerySet.get_or_create

    update_or_create = RpcBaseQuerySet.update_or_create

    bulk_update = RpcBaseQuerySet.bulk_create

    @utils.value_method
    def count(self, *args, **kwargs):
        pass

    def in_bulk(self, *args, **kwargs):
        pass

    def iterator(self, *args, **kwargs):
        pass

    @utils.single_object_method
    def latest(self, *args, **kwargs):
        pass

    @utils.single_object_method
    def earliest(self, *args, **kwargs):
        pass

    @utils.single_object_method
    def first(self, *args, **kwargs):
        pass

    @utils.single_object_method
    def last(self, *args, **kwargs):
        pass

    @utils.value_method
    def aggregate(self, *args, **kwargs):
        pass

    @utils.value_method
    def exists(self, *args, **kwargs):
        pass

    @utils.value_method
    def update(self, *args, **kwargs):
        pass

    @utils.value_method
    def delete(self, *args, **kwargs):
        pass

    def as_manager(self, *args, **kwargs):
        base_manager = type(self.model.objects)
        manager_class = type("ManagerFromQuerySet",
                             (base_manager,),
                             {'_queryset_class': type(self)})
        return manager_class()
