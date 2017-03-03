# coding: utf-8
import functools


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

    inner._is_rpc_method = True
    return inner


def manager_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        method = getattr(self.get_queryset(), func.__name__)
        return method(*args, **kwargs)

    return inner


def is_queryset_method(method):
    return getattr(method, '_is_queryset_method', None)


def is_rpc_method(method):
    return getattr(method, '_is_rpc_method', None)
