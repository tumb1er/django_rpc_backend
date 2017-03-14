# coding: utf-8
from django.test import TestCase

from django_rpc.models import RpcModel
from rpc_client.models import ClientModel
from rpc_client.tests import base
from rpc_server.models import ServerModel


class DjangoQuerySetTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                             TestCase):
    client_model = ClientModel
    server_model = ServerModel
    fixtures = ['tests.json']

#
# class NativeModel(RpcModel):
#     class Rpc:
#         app_label = 'rpc_server'
#         name = 'ServerModel'
#
#
# class NativeQuerySetTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
#                              TestCase):
#     client_model = NativeModel
#     server_model = ServerModel
#     fixtures = ['tests.json']
