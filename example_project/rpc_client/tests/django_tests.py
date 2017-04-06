# coding: utf-8

from django.db import models
from django.test import TestCase
from mock import mock

from django_rpc.models import RpcModel
from django_rpc.models.fields import ForeignKey
from rpc_client.models import ClientModel, FKClientModel
from rpc_client.tests import base
from rpc_server.models import ServerModel, FKModel


class DjangoQuerySetTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                             TestCase):
    client_model = ClientModel
    server_model = ServerModel
    fk_client_model = FKClientModel
    fk_model =  FKModel
    fixtures = ['tests.json']


class DisabledRpcDjangoTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                                TestCase):
    client_model = ClientModel
    server_model = ServerModel
    fk_model = FKModel
    fk_client_model = FKClientModel
    fixtures = ['tests.json']

    def setUp(self):
        super().setUp()
        self._patchers = []

        p = mock.patch(
            'django_rpc.routers.RpcRouter.is_rpc_model',
            return_value=False)
        p.start()
        self._patchers.append(p)

        p = mock.patch('celery.Task.apply_async')
        self.apply_mock = p.start()
        self._patchers.append(p)

        self.client_model._meta.db_table = self.server_model._meta.db_table
        self.fk_client_model._meta.db_table = self.fk_model._meta.db_table
        self.signal_model = self.client_model

    def testUsing(self):
        qs = self.client_model.objects.using('some_db')
        self.assertIsInstance(qs, models.QuerySet)

    def testSelectForUpdate(self):
        qs = self.client_model.objects.select_for_update()
        self.assertIsInstance(qs, models.QuerySet)

    def testRaw(self):
        qs = self.client_model.objects.raw('SELECT 1')
        self.assertIsInstance(qs, models.query.RawQuerySet)

    def tearDown(self):
        super().tearDown()
        self.assertFalse(self.apply_mock.called)
        for p in self._patchers:
            p.stop()


class NativeFKModel(RpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'FKModel'


class NativeModel(RpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'ServerModel'

    fk = ForeignKey(NativeFKModel)


class NativeQuerySetTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                             TestCase):
    client_model = NativeModel
    server_model = ServerModel
    fk_client_model = NativeFKModel
    fk_model = FKModel
    fixtures = ['tests.json']
