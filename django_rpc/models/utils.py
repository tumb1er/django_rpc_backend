# coding: utf-8
import functools


def queryset_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        return self._trace(func.__name__, *args, **kwargs)
    inner._is_queryset_method = True
    return inner


def single_object_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        qs = self._clone()
        # noinspection PyProtectedMember
        qs._trace(func.__name__, *args, **kwargs)
        obj = next(iter(qs))
        return obj
    inner._is_queryset_method = True
    return inner


def value_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        qs = self._clone()
        # noinspection PyProtectedMember
        qs._trace(func.__name__, *args, **kwargs)
        qs._return_native = True
        obj = next(iter(qs))
        return obj
    inner._is_queryset_method = True
    return inner


def values_queryset_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        qs = self._trace(func.__name__, *args, **kwargs)
        qs._return_native = True
        return qs
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
