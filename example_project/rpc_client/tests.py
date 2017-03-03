import mock
from django.test import TestCase
from django.conf import settings

from rpc_client.models import ClientModel
from rpc_server.models import ServerModel
from django_rpc.celery import client, tasks

# noinspection PyUnresolvedReferences
@mock.patch.dict(settings.DATABASES['rpc'], {'CELERY_ALWAYS_EAGER': True})
@mock.patch.object(client, 'RpcTaskBase', new_callable=mock.PropertyMock(
    return_value=tasks.FetchTask))
class BaseRpcClientTestCase(TestCase):

    def setUp(self):
        self.server = ServerModel.objects.create(char_field='first')

        self.model = ClientModel

    def assertObjectsEqual(self, o1, o2):
        del o1._state
        del o2._state
        self.assertDictEqual(o1.__dict__, o2.__dict__)

    def testGet(self, _):
        res = self.model.objects.get(pk=self.server.pk)
        self.assertObjectsEqual(res, self.server)

    def testCreate(self):
        c = self.model.objects.create(char_field='test')
        s = ServerModel.objects.get(pk=c.pk)
        self.assertObjectsEqual(c, s)
