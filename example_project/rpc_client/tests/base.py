# coding: utf-8
from django.test import TestCase
from typing import Type


from django_rpc.models.base import RpcModel


class BaseRpcTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        __import__('django_rpc.celery.tasks')


class QuerySetTestsMixin(object):
    client_model = None  # type: Type[RpcModel]
    server_model = None
    """ :type server_model: rpc_server.models.ServerModel"""

    # noinspection PyProtectedMember
    def assertObjectsEqual(self, o1, o2):
        if hasattr(o1, '_state'):
            del o1._state
        if hasattr(o2, '_state'):
            del o2._state
        # noinspection PyUnresolvedReferences
        self.assertDictEqual(o1.__dict__, o2.__dict__)

    def setUp(self):
        super(QuerySetTestsMixin, self).setUp()
        self.s1 = self.server_model.objects.get(pk=1)
        self.s2 = self.server_model.objects.get(pk=2)

    def testGet(self):
        res = self.client_model.objects.get(pk=self.s1.pk)
        self.assertObjectsEqual(res, self.s1)

    def testCreate(self):
        c = self.client_model.objects.create(char_field='test', int_field=1)
        s = self.server_model.objects.get(pk=c.pk)
        self.assertObjectsEqual(c, s)

    def testBulkCreate(self):
        server_count = self.server_model.objects.count()
        c2 = self.client_model(char_field='2', int_field=1)
        c3 = self.client_model(char_field='3', int_field=1)
        ret = self.client_model.objects.bulk_create([c2, c3])
        self.assertEqual(len(ret), 2)
        self.assertIsInstance(ret[0], self.client_model)
        self.assertObjectsEqual(ret[0], c2)
        self.assertEqual(self.server_model.objects.count(), server_count + 2)
        s2, s3 = self.server_model.objects.filter(pk__gt=self.s2.pk)
        s2.id = None
        s3.id = None
        self.assertObjectsEqual(c2, s2)
        self.assertObjectsEqual(c3, s3)

    def testGetOrCreate(self):
        c, created = self.client_model.objects.get_or_create(
            char_field='first',
            defaults={'int_field': 1})
        self.assertFalse(created)
        self.assertIsInstance(c, self.client_model)
        self.assertObjectsEqual(c, self.s1)
