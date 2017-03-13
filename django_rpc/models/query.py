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
        return result.__iter__()


class RpcQuerySet(RpcBaseQuerySet):

    @queryset_method
    def filter(self, *args, **kwargs):
        pass

    @queryset_method
    def exclude(self, *args, **kwargs):
        pass
