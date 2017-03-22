# coding: utf-8
import functools


def queryset_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        return self._trace(func.__name__, args, kwargs)
    return inner


def single_object_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        qs = self._trace(func.__name__, args, kwargs)
        # noinspection PyProtectedMember
        data = qs.fetch()
        instance = qs.instantiate(data)
        return instance
    return inner


def value_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        qs = self._trace(func.__name__, args, kwargs)
        qs._return_native = True
        # noinspection PyProtectedMember
        result = qs.fetch()
        return result
    return inner


def values_queryset_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        qs = self._trace(func.__name__, args, kwargs, iterable='ValuesIterable')
        qs._return_native = True
        return qs
    return inner


def manager_method(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        method = getattr(self.get_queryset(), func.__name__)
        return method(*args, **kwargs)

    return inner
