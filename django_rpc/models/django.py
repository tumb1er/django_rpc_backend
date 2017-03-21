# coding: utf-8

from __future__ import absolute_import

import six
from django.conf import settings
from django.db import models, router
from django.utils.functional import cached_property
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
    def to_internal_value(self, data):
        return data


class DjangoRpcQuerySet(RpcQuerySet, models.QuerySet):

    def __init__(self, model=None, query=None, using=None, hints=None):
        RpcQuerySet.__init__(self, model)
        # noinspection PyTypeChecker
        models.QuerySet.__init__(self, model=model, query=query, using=using,
                                 hints=hints)

    def __iter__(self):
        result = self._fetch()

        for item in result.__iter__():
            if self._return_native:
                yield item
                continue
            obj = self._instantiate(item)
            for f in self._exclude_fields:
                if hasattr(obj, f):
                    delattr(obj, f)
            if self._field_list:
                for k in list(obj.__dict__.keys()):
                    if k not in self._field_list:
                        delattr(obj, k)
            yield obj

    @staticmethod
    def _get_fields(obj):
        # noinspection PyProtectedMember
        return [f.attname for f in obj._meta.fields]

    def _get_pk_field(self):
        # noinspection PyProtectedMember
        return self.model._meta.pk.attname

    def get_or_create(self, *args, **kwargs):
        assert not args, "args not supported for create"

        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, kwargs)

        instance = self._instantiate(data)

        return instance, created

    def _instantiate(self, data):
        instance = self.model()
        instance.__dict__.update(self._serializer.to_internal_value(data))
        return instance

    def update_or_create(self, *args, **kwargs):
        assert not args, "args not supported for create"

        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, kwargs, update=True)

        instance = self._instantiate(data)

        return instance, created

    @cached_property
    def _serializer(self):

        fields = self._field_list or ()
        pk_name = self.model._meta.pk.attname

        if fields or self._extra_fields:
            if not fields:
                fields = tuple([f.attname for f in self.model._meta.fields])
            all_fields = set(fields + self._extra_fields + (pk_name,))
            serializer_fields = [f for f in all_fields
                                 if f not in self._exclude_fields]
            serializer_exclude = None
        elif self._exclude_fields:
            serializer_fields = None
            serializer_exclude = self._exclude_fields
        else:
            serializer_fields = '__all__'
            serializer_exclude = None

        class Meta:
            model = self.model
            fields = serializer_fields
            exclude = serializer_exclude

        attrs = {'Meta': Meta}
        for f in self._extra_fields:
            attrs[f] = NativeField()

        Serializer = type('Serializer', (serializers.ModelSerializer,), attrs)

        # noinspection PyProtectedMember
        opts = self.model._meta
        s = Serializer()
        s.fields[opts.pk.attname].read_only = False
        return s


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
