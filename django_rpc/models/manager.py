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
    def exclude(self, *args, **kwargs):
        pass

    @manager_method
    def annotate(self, *args, **kwargs):
        pass

    @manager_method
    def order_by(self, *args, **kwargs):
        pass

    @manager_method
    def reverse(self, *args, **kwargs):
        pass

    @manager_method
    def distinct(self, *args, **kwargs):
        pass

    @manager_method
    def values(self, *args, **kwargs):
        pass

    @manager_method
    def values_list(self, *args, **kwargs):
        pass

    @manager_method
    def dates(self, *args, **kwargs):
        pass

    @manager_method
    def datetimes(self, *args, **kwargs):
        pass

    @manager_method
    def none(self, *args, **kwargs):
        pass

    @manager_method
    def all(self, *args, **kwargs):
        pass

    @manager_method
    def select_related(self, *args, **kwargs):
        pass

    @manager_method
    def prefetch_related(self, *args, **kwargs):
        pass

    @manager_method
    def extra(self, *args, **kwargs):
        pass

    @manager_method
    def defer(self, *args, **kwargs):
        pass

    @manager_method
    def only(self, *args, **kwargs):
        pass

    @manager_method
    def using(self, *args, **kwargs):
        pass

    @manager_method
    def select_for_update(self, *args, **kwargs):
        pass

    @manager_method
    def raw(self, *args, **kwargs):
        pass

    @manager_method
    def get(self, *args, **kwargs):
        pass

    @manager_method
    def create(self, *args, **kwargs):
        pass

    @manager_method
    def get_or_create(self, *args, **kwargs):
        pass

    @manager_method
    def update_or_create(self, *args, **kwargs):
        pass

    @manager_method
    def bulk_create(self, *args, **kwargs):
        pass

    @manager_method
    def count(self, *args, **kwargs):
        pass

    @manager_method
    def in_bulk(self, *args, **kwargs):
        pass

    @manager_method
    def iterator(self, *args, **kwargs):
        pass

    @manager_method
    def latest(self, *args, **kwargs):
        pass

    @manager_method
    def earliest(self, *args, **kwargs):
        pass

    @manager_method
    def first(self, *args, **kwargs):
        pass

    @manager_method
    def last(self, *args, **kwargs):
        pass

    @manager_method
    def aggregate(self, *args, **kwargs):
        pass

    @manager_method
    def exists(self, *args, **kwargs):
        pass

    @manager_method
    def update(self, *args, **kwargs):
        pass

    @manager_method
    def delete(self, *args, **kwargs):
        pass

