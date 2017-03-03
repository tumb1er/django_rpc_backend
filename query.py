# coding: utf-8
import functools

import six


def queryset_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        return self._trace(func.__name__, *args, **kwargs)
    inner._is_queryset_method = True
    return inner


def rpc_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        qs = self._clone()
        # noinspection PyProtectedMember
        qs._trace(func.__name__, *args, **kwargs)
        raise NotImplementedError()

    inner._is_queryset_method = True
    return inner


def manager_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        queryset_method = getattr(self.get_queryset(), func.__name__)
        return queryset_method(*args, **kwargs)

    return inner


def is_queryset_method(method):
    return getattr(method, '_is_queryset_method', None)


class RpcBaseQuerySet(object):
    """ Django-style реализация конфигуратора запроса к rpc."""

    def __init__(self, model):
        self.__trace = ()
        self.model = model

    def _trace(self, method, *args, **kwargs):
        clone = self.__class__(self.model)
        # noinspection PyTypeChecker
        clone.__trace = self.__trace + ((method, args, kwargs),)
        return clone


class RpcManagerBase(object):
    _queryset_class = None

    def __init__(self):
        self.model = None

    def contribute_to_class(self, model):
        self.model = model

    def __get__(self, instance, owner):
        return self

    def get_queryset(self):
        return self._queryset_class(model=self.model)

    @manager_method
    def filter(self, *args, **kwargs):
        pass

    @manager_method
    def exclude(self, *args, **kwargs):
        pass




qs = RpcModel.objects.filter(a=1)
qs = qs.exclude(b=2)
