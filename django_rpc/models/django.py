# coding: utf-8

from __future__ import absolute_import

import six
from django.conf import settings
from django.db import models, router
from rest_framework import serializers

from django_rpc.celery import defaults
from django_rpc.celery.client import RpcClient
from django_rpc.models import base, utils
from django_rpc.models.query import RpcQuerySet


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


class DjangoRpcQuerySet(models.QuerySet, RpcQuerySet):

    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        RpcQuerySet.__init__(self, model)

    def iterator(self):
        self.query.rpc_trace = self.rpc_trace
        return super(DjangoRpcQuerySet, self).iterator()

    @utils.single_object_method
    def get(self, *args, **kwargs):
        pass

    def get_or_create(self, *args, **kwargs):
        assert not args, "args not supported for create"
        db = router.db_for_write(self.model)
        if not rpc_enabled(db):
            return models.QuerySet.get_or_create(self, **kwargs)

        rpc = self.model.Rpc
        client = RpcClient.from_db(rpc.db)
        data, created = client.get_or_create(
            rpc.app_label, rpc.name, **kwargs)

        class Serializer(serializers.ModelSerializer):
            class Meta:
                model = self.model
                fields = '__all__'

        # noinspection PyProtectedMember
        opts = self.model._meta
        s = Serializer()
        s.fields[opts.pk.attname].read_only = False

        instance = self.model()
        instance.__dict__.update(s.to_internal_value(data))

        return instance, created


class DjangoRpcManager(models.manager.Manager, base.RpcManager):
    _queryset_class = DjangoRpcQuerySet


class DjangoRpcModel(six.with_metaclass(DjangoRpcModelBase,
                                        base.RpcModel, models.Model)):
    class Meta:
        abstract = True

    objects = DjangoRpcManager()
