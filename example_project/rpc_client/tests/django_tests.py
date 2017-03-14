# coding: utf-8

from rpc_client.models import ClientModel
from rpc_client.tests import base
from rpc_server.models import ServerModel


class DjangoQuerySetTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase):
    client_model = ClientModel
    server_model = ServerModel
    fixtures = ['tests.json']
