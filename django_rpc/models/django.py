# coding: utf-8

from __future__ import absolute_import

import six
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models, router
from rest_framework import serializers

from django_rpc.celery import defaults
from django_rpc.celery.client import RpcClient
from django_rpc.models import base
from django_rpc.models.query import RpcQuerySet


__all__ = [
    'DjangoRpcModelBase',
    'DjangoRpcQuerySet',
    'DjangoRpcManager',
    'DjangoRpcModel'
]


def rpc_enabled(db):
    return settings.DATABASES[db]['ENGINE'] == defaults.ENGINE


class DjangoRpcModelBase(base.RpcModelBase, models.base.ModelBase):
    # noinspection PyMethodOverriding
    @classmethod
    def init_rpc_meta(mcs, name, bases, attrs):
        meta = attrs.get('Meta')
        if meta and getattr(meta, 'abstract'):
            return

        super(DjangoRpcModelBase, mcs).init_rpc_meta(name, bases, attrs)


class NativeField(serializers.Field):
    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        return data


class DjangoRpcQuerySet(RpcQuerySet, models.QuerySet):

    def __init__(self, model=None, query=None, using=None, hints=None):
        RpcQuerySet.__init__(self, model)
        # noinspection PyTypeChecker
        models.QuerySet.__init__(self, model=model, query=query, using=using,
                                 hints=hints)
        self._iterable_class = RpcQuerySet._iterable_class

    def update_model(self, obj, data):
        patched = {}
        for k, v in data.items():
            try:
                f = self.model._meta.get_field(k)
            except FieldDoesNotExist:
                f = None
            if f and f.is_relation and f.name == k:
                cache_name = f.get_cache_name()
                qs = f.related_model.objects.get_queryset()
                related_obj = qs.instantiate(v)
                patched[cache_name] = related_obj
            else:
                patched[k] = v
        super().update_model(obj, patched)

    @staticmethod
    def _get_fields(obj):
        # noinspection PyProtectedMember
        return [f.attname for f in obj._meta.fields]

    def _get_pk_field(self):
        # noinspection PyProtectedMember
        return self.model._meta.pk.attname

    def _get_or_update_or_create(self, args, kwargs, update=False):
        assert not args, "args not supported for create"
        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, kwargs, update=update)
        instance = self.instantiate(data)
        return instance, created

    def get_or_create(self, *args, **kwargs):
        return self._get_or_update_or_create(args, kwargs, update=False)

    def update_or_create(self, *args, **kwargs):
        return self._get_or_update_or_create(args, kwargs, update=True)

    def select_for_update(self, *args, **kwargs):
        raise NotImplementedError()

    def raw(self, *args, **kwargs):
        raise NotImplementedError()

    def using(self, *args, **kwargs):
        raise NotImplementedError()


class DjangoRpcManager(models.manager.Manager, base.RpcManager):
    _rpc_queryset_class = DjangoRpcQuerySet

    def get_queryset(self):
        if rpc_enabled(router.db_for_read(self.model)):
            return self._rpc_queryset_class(
                model=self.model, using=self._db, hints=self._hints)
        return super().get_queryset()


class DjangoRpcModel(six.with_metaclass(DjangoRpcModelBase,
                                        base.RpcModel, models.Model)):
    class Meta:
        abstract = True

    objects = DjangoRpcManager()

    save = models.Model.save

    delete = models.Model.delete
