# coding: utf-8
import signal

from celery.bin.celery import CeleryCommand
from django.db import models
from django.test import TestCase
from mock import mock
from subprocess import Popen

from multiprocessing import Process

from django_rpc.celery.app import celery
from django_rpc.celery.client import RpcClient
from django_rpc.models import RpcModel
from rpc_client.models import ClientModel
from rpc_client.tests import base
from rpc_server.models import ServerModel


class DjangoQuerySetTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                             TestCase):
    client_model = ClientModel
    server_model = ServerModel
    fixtures = ['tests.json']


class DisabledRpcDjangoTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                                TestCase):
    client_model = ClientModel
    server_model = ServerModel
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


class NativeModel(RpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'ServerModel'


class NativeQuerySetTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                             TestCase):
    client_model = NativeModel
    server_model = ServerModel
    fixtures = ['tests.json']


def start_celery(argv):
    cmd = CeleryCommand()
    cmd.maybe_patch_concurrency()
    cmd.execute_from_commandline(argv)


class NativeCeleryTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                           TestCase):
    client_model = NativeModel
    server_model = ServerModel
    fixtures = ['tests.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cmd = 'celery worker -c 1 -A django_rpc.celery.app --loglevel=DEBUG'
        cls.celery = Process(target=start_celery, args=[cmd.split(' ')])
        cls.celery.start()
        celery.conf.update(CELERY_ALWAYS_EAGER=False)
        cls.rpc_client = RpcClient.from_db('rpc')
        conf = cls.rpc_client._app.conf
        cls.eager = conf['CELERY_ALWAYS_EAGER']
        conf['CELERY_ALWAYS_EAGER'] = False

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.celery.terminate()
        cls.rpc_client._app.conf['CELERY_ALWAYS_EAGER'] = cls.eager
