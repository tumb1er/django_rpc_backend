# coding: utf-8
from django_rpc.models.query import RpcQuerySet
from django_rpc.models.utils import manager_method


class RpcManagerBase(object):
    _queryset_class = RpcQuerySet

    def __init__(self):
        self.model = None

    def contribute_to_class(self, model, name):
        self.model = model

    def __get__(self, instance, owner):
        return self

    def get_queryset(self):
        return self._queryset_class(model=self.model)


class RpcManager(RpcManagerBase):

    @manager_method
    def filter(self, *args, **kwargs):
        pass

    @manager_method
    def all(self, *args, **kwargs):
        pass

    @manager_method
    def exclude(self, *args, **kwargs):
        pass

    @manager_method
    def create(self, *args, **kwargs):
        pass

    @manager_method
    def get_or_create(self, *args, **kwargs):
        pass
