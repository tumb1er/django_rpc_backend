# coding: utf-8

from __future__ import absolute_import

import six
from django.db import models

from django_rpc.models import base, query


class DjangoRpcModelBase(base.RpcModelBase, models.base.ModelBase):
    @classmethod
    def init_rpc_meta(cls, name, bases, attrs):
        meta = attrs.get('Meta')
        if meta and getattr(meta, 'abstract'):
            return

        super(DjangoRpcModelBase, cls).init_rpc_meta(name, bases, attrs)


class DjangoRpcQuerySet(query.RpcQuerySet, models.QuerySet):
    def iterator(self):
        self.query.rpc_trace = self.rpc_trace
        return super(DjangoRpcQuerySet, self).iterator()


class DjangoRpcManager(models.manager.Manager, base.RpcManager):
    _queryset_class = DjangoRpcQuerySet


class DjangoRpcModel(six.with_metaclass(DjangoRpcModelBase,
                                        base.RpcModel, models.Model)):
    class Meta:
        abstract = True

    objects = DjangoRpcManager()