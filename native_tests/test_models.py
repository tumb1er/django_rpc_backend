# coding: utf-8
from unittest import TestCase

import mock
# from django.test import TestCase

from django_rpc.models import RpcModel


class ClientModel(RpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'ServerModel'


class NativeQuerySetTestCase(TestCase):
    def setUp(self):
        self._patchers = []
        p = mock.patch('django_rpc.celery.client.RpcTaskBase.delay')
        self.fetch_mock = p.start()
        self._patchers.append(p)

    def tearDown(self):
        for p in self._patchers:
            p.stop()

    def testQuerySetFilter(self):
        list(ClientModel.objects.filter(a=1))
        self.assertRpcFetchCall(ClientModel,
                                ('filter', (), {'a': 1}))

    def assertRpcFetchCall(self, model, *trace):
        opts = getattr(model, 'Rpc')
        self.fetch_mock.assert_called_once_with(
            opts.app_label, opts.name, trace)
