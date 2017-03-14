# coding: utf-8

from django_rpc.celery.client import RpcClient
from django_rpc.models import utils


class RpcBaseQuerySet(object):
    """ Django-style реализация конфигуратора запроса к rpc."""

    def __init__(self, model):
        self.model = model
        self.__trace = ()
        self._return_native = False
        super(RpcBaseQuerySet, self).__init__()

    def _trace(self, method, *args, **kwargs):
        clone = self.__class__(model=self.model)
        # noinspection PyTypeChecker
        clone.__trace = self.__trace + ((method, args, kwargs),)
        return clone

    @property
    def rpc_trace(self):
        return self.__trace

    def __iter__(self):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        result = client.fetch(opts.app_label, opts.name, self.__trace)
        for item in result.__iter__():
            obj = self.model()
            obj.__dict__.update(item)
            yield obj

    def create(self, *args, **kwargs):
        opts = self.model.Rpc
        client = RpcClient.from_db(opts.db)
        assert not args, "args not supported for create"
        fields = list(kwargs.keys())
        data = [kwargs]
        result = client.insert(opts.app_label, opts.name, data, fields,
                               return_id=True)
        return result

    def get_or_create(self, *args, **kwargs):
        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        assert not args, "args not supported for create"
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, **kwargs)
        instance = self.model()
        instance.__dict__.update(data)

        return instance, created


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

    @utils.queryset_method
    def none(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def all(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def select_related(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def prefetch_related(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def extra(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def defer(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def only(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def using(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def select_for_update(self, *args, **kwargs):
        pass

    @utils.queryset_method
    def raw(self, *args, **kwargs):
        pass

    #
    # methods-that-do-not-return-querysets
    #

    @utils.single_object_method
    def get(self, *args, **kwargs):
        pass

    @utils.single_object_method
    def create(self, *args, **kwargs):
        pass

    def get_or_create(self, *args, **kwargs):
        pass

    def update_or_create(self, *args, **kwargs):
        pass

    def bulk_create(self, *args, **kwargs):
        pass

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
        pass