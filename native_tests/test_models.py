# coding: utf-8
from unittest import TestCase

import mock

from django_rpc.celery.client import RpcClient
from django_rpc.models import RpcModel


class ClientModel(RpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'ServerModel'


class NativeQuerySetTestCase(TestCase):
    # noinspection PyUnresolvedReferences
    def setUp(self):
        self._patchers = []
        self.rpc_client = RpcClient.from_db(ClientModel.Rpc.db)
        p = mock.patch.object(self.rpc_client._fetch, 'delay')
        self.fetch_mock = p.start()
        self._patchers.append(p)

        p = mock.patch.object(self.rpc_client._insert, 'delay')
        self.insert_mock = p.start()
        self._patchers.append(p)

    def tearDown(self):
        for p in self._patchers:
            p.stop()

    def testQuerySetFilter(self):
        list(ClientModel.objects.filter(a=1))
        self.assertRpcFetchCall(ClientModel,
                                ('filter', (), {'a': 1}))

    def testQuerySetCreate(self):
        self.fetch_mock.return_value.get.return_value = 2
        ClientModel.objects.create(a=1)
        self.assertRpcInsertCall(ClientModel, [{'a': 1}])

    def assertRpcFetchCall(self, model, *trace):
        opts = getattr(model, 'Rpc')
        self.fetch_mock.assert_called_once_with(
            opts.app_label, opts.name, trace)

    def assertRpcInsertCall(self, model, data, return_id=True):
        opts = getattr(model, 'Rpc')
        self.insert_mock.assert_called_once_with(
            opts.app_label, opts.name, data, list(data[0].keys()), raw=False,
            return_id=return_id)
