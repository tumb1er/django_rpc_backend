import mock
from celery import Celery
from django.conf import settings
from django.test import TestCase
from django.utils.timezone import now

from django_rpc.celery.client import RpcClient
from django_rpc.celery import tasks
from django_rpc.celery.conf import settings as rpc_settings
from rpc_client.models import ClientModel
from rpc_server.models import ServerModel


class BaseRpcClientTestCase(TestCase):

    def setUp(self):
        self.server = ServerModel.objects.create(char_field='first')

        self.model = ClientModel
        self.client = RpcClient.from_db(ClientModel.Rpc.db)

    def assertObjectsEqual(self, o1, o2):
        del o1._state
        del o2._state
        self.assertDictEqual(o1.__dict__, o2.__dict__)

    def testGet(self):
        res = self.model.objects.get(pk=self.server.pk)
        self.assertObjectsEqual(res, self.server)

    def testCreate(self):
        c = self.model.objects.create(char_field='test', dt_field=now())
        s = ServerModel.objects.get(pk=c.pk)
        self.assertObjectsEqual(c, s)

    def testBulkCreate(self):
        c2 = ClientModel(char_field='2', dt_field=now())
        c3 = ClientModel(char_field='3', dt_field=now())
        ret = ClientModel.objects.bulk_create([c2, c3])
        self.assertEqual(ServerModel.objects.count(), 3)
        s2, s3 = ServerModel.objects.filter(pk__gt=self.server.pk)
        s2.id = None
        s3.id = None
        self.assertObjectsEqual(c2, s2)
        self.assertObjectsEqual(c3, s3)
