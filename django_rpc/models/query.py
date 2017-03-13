# coding: utf-8

from django_rpc.celery.client import RpcClient
from django_rpc.models.utils import queryset_method


class RpcBaseQuerySet(object):
    """ Django-style реализация конфигуратора запроса к rpc."""

    def __init__(self, model):
        self.model = model
        self.__trace = ()
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

    @queryset_method
    def filter(self, *args, **kwargs):
        pass

    @queryset_method
    def all(self, *args, **kwargs):
        pass

    @queryset_method
    def exclude(self, *args, **kwargs):
        pass
