# coding: utf-8
from unittest import TestCase

from typing import Type


from django_rpc.models.base import RpcModel


class BaseRpcTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        __import__('django_rpc.celery.tasks')


class QuerySetTestsMixin(TestCase):
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

    def testFilter(self):
        qs = self.client_model.objects.filter(pk=self.s1.pk)
        self.assertQuerySetEqual(qs, [self.s1])

    def testExclude(self):
        qs = self.client_model.objects.exclude(pk=self.s1.pk)
        self.assertQuerySetEqual(qs, [self.s2])

    def testAnnotate(self):
        # FIXME: Требуются условия, при которых возможно получение дублей
        self.skipTest("TBD: QuerySet.annotate")

    def testOrderBy(self):
        qs = self.client_model.objects.order_by('-pk')
        self.assertQuerySetEqual(qs, [self.s2, self.s1])

    def testReverse(self):
        qs = self.client_model.objects.order_by('pk').reverse()
        self.assertQuerySetEqual(qs, [self.s2, self.s1])

    def testDistinct(self):
        # FIXME: Требуются условия, при которых возможно получение дублей
        self.skipTest("TBD: QuerySet.distinct")

    def testValues(self):
        data = list(self.client_model.objects.values('char_field'))
        expected = list(self.server_model.objects.values('char_field'))
        self.assertEqual(len(data), len(expected))
        for d, e in zip(data, expected):
            self.assertDictEqual(d, e)

    def testValuesList(self):
        data = list(self.client_model.objects.values_list('char_field'))
        expected = list(self.server_model.objects.values_list('char_field'))
        self.assertEqual(len(data), len(expected))
        for d, e in zip(data, expected):
            self.assertTupleEqual(d, e)

    def testValuesListFlat(self):
        data = list(self.client_model.objects.values_list(
            'char_field', flat=True))
        expected = list(self.server_model.objects.values_list(
            'char_field', flat=True))
        self.assertListEqual(data, expected)

    def testDates(self):
        # FIXME: сериализация DateTime
        self.skipTest("TBD: QuerySet.dates")

    def testDateTimes(self):
        # FIXME: сериализация DateTime
        self.skipTest("TBD: QuerySet.datetimes")

    def testNone(self):
        with self.assertRaises(NotImplementedError):
            self.client_model.objects.none()

    def testAll(self):
        qs = self.client_model.objects.all()
        expected = self.server_model.objects.all()
        self.assertQuerySetEqual(qs, expected)

    def testSelectRelated(self):
        # FIXME: сериализация связанных объектов
        self.skipTest("TBD: QuerySet.select_related")

    def testPrefetchRelated(self):
        # FIXME: сериализация связанных объектов
        self.skipTest("TBD: QuerySet.prefetch_related")

    def testExtra(self):
        qs = self.client_model.objects.extra(select={'some': '%s + %s'},
                                             select_params=(1, 2))
        expected = self.server_model.objects.extra(select={'some': '%s + %s'},
                                                   select_params=(1, 2))
        self.assertQuerySetEqual(qs, expected)

    def testDefer(self):
        qs = self.client_model.objects.defer('int_field')
        expected = self.server_model.objects.defer('int_field')
        self.assertQuerySetEqual(qs, expected)

    def testDeferReset(self):
        qs = self.client_model.objects.defer('int_field').defer(None)
        expected = self.server_model.objects.all()
        self.assertQuerySetEqual(qs, expected)

    def testDeferDefer(self):
        qs = self.client_model.objects.defer('int_field').defer('char_field')
        expected = self.server_model.objects.defer(
            'int_field').defer('char_field')
        self.assertQuerySetEqual(qs, expected)

    def testOnly(self):
        qs = self.client_model.objects.only('char_field')
        expected = self.server_model.objects.only('char_field')
        self.assertQuerySetEqual(qs, expected)

    def testOnlyOnly(self):
        qs = self.client_model.objects.only(
            'char_field', 'int_field').only('char_field')
        expected = self.server_model.objects.only(
            'char_field', 'int_field').only('char_field')
        self.assertQuerySetEqual(qs, expected)

    def testOnlyDefer(self):
        qs = self.client_model.objects.only(
            'char_field', 'int_field').defer('char_field')
        expected = self.server_model.objects.only(
            'char_field', 'int_field').defer('char_field')
        self.assertQuerySetEqual(qs, expected)

    def testDeferOnly(self):
        qs = self.client_model.objects.defer(
            'char_field').only('char_field')
        expected = self.server_model.objects.defer(
            'char_field').only('char_field')
        self.assertQuerySetEqual(qs, expected)

    def testUsing(self):
        with self.assertRaises(NotImplementedError):
            self.client_model.objects.using('some_db')

    def testSelectForUpdate(self):
        with self.assertRaises(NotImplementedError):
            self.client_model.objects.select_for_update()

    def testRaw(self):
        with self.assertRaises(NotImplementedError):
            self.client_model.objects.raw("SELECT 1")

    def testCreate(self):
        c = self.client_model.objects.create(char_field='test', int_field=1)
        s = self.server_model.objects.get(pk=c.id)
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

    def assertQuerySetEqual(self, qs, expected):
        result = list(qs)
        self.assertEqual(len(result), len(expected))
        for real, exp in zip(result, expected):
            self.assertObjectsEqual(real, exp)
