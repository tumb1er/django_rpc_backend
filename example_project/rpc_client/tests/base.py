# coding: utf-8
from unittest import TestCase

import pytz
from celery import Task
from django.db import models
from django.utils.timezone import now
from mock import mock
from typing import Type

from django_rpc.celery import codecs
from django_rpc.models.base import RpcModel


def encode_decode(data):
    data = codecs.x_rpc_json_dumps(data)
    return codecs.x_rpc_json_loads(data)


def celery_passthrough(task, *args, **kwargs):
    """ Simulate celery task and result transport.
    
    In CELERY_ALWAYS_EAGER mode no celery serializers are called.
    """
    args, kwargs = encode_decode([args, kwargs])
    result = task.apply(*args, **kwargs)
    # noinspection PyProtectedMember
    result._result = encode_decode(result._result)
    return result


class BaseRpcTestCase(TestCase):

    _apply_async_patcher = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        __import__('django_rpc.celery.tasks')
        # noinspection PyUnresolvedReferences
        p = mock.patch.object(Task, 'apply_async',
                              side_effect=celery_passthrough, autospec=True)
        cls._apply_async_patcher = p
        p.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if hasattr(cls._apply_async_patcher, 'is_local'):
            cls._apply_async_patcher.stop()


class QuerySetTestsMixin(TestCase):
    client_model = None  # type: Type[RpcModel]
    server_model = None
    fk_model = None
    """ 
    :type server_model: rpc_server.models.ServerModel
    :type fk_model: rpc_server.models.FKModel
    
    """

    # noinspection PyProtectedMember
    def assertObjectsEqual(self, o1, o2):
        if hasattr(o1, '_state'):
            del o1._state
        if hasattr(o2, '_state'):
            del o2._state
        self.assertDictEqual(o1.__dict__, o2.__dict__)

    def setUp(self):
        super(QuerySetTestsMixin, self).setUp()
        self.s1 = self.server_model.objects.get(pk=1)
        self.s2 = self.server_model.objects.get(pk=2)

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
            self.assertIsInstance(d, (list, tuple))
            d = tuple(d)
            self.assertTupleEqual(d, e)

    def testValuesListFlat(self):
        data = list(self.client_model.objects.values_list(
            'char_field', flat=True))
        expected = list(self.server_model.objects.values_list(
            'char_field', flat=True))
        self.assertListEqual(data, expected)

    def testDates(self):
        data = list(self.client_model.objects.dates('dt_field', 'year'))
        expected = list(self.server_model.objects.dates('dt_field', 'year'))
        self.assertListEqual(data, expected)

    def testDateTimes(self):
        data = list(self.client_model.objects.datetimes('dt_field', 'year'))
        expected = list(self.server_model.objects.datetimes('dt_field', 'year'))
        self.assertListEqual(data, expected)

    def testDateTimesTZInfo(self):
        tz = pytz.timezone('Europe/Moscow')
        data = list(self.client_model.objects.datetimes(
            'dt_field', 'minute', tzinfo=tz))
        expected = list(self.server_model.objects.datetimes(
            'dt_field', 'minute', tzinfo=tz))
        self.assertListEqual(data, expected)

    def testNone(self):
        # FIXME: убрать вызов fetch task
        qs = self.client_model.objects.none()
        self.assertListEqual(list(qs), [])

    def testAll(self):
        qs = self.client_model.objects.all()
        expected = self.server_model.objects.all()
        self.assertQuerySetEqual(qs, expected)

    def testSelectRelated(self):
        qs = self.client_model.objects.filter(pk=1).select_related('fk')
        c = list(qs)[0]
        s = self.server_model.objects.filter(pk=1).select_related('fk')[0]
        self.assertTrue(hasattr(c, 'fk'))
        self.assertObjectsEqual(c.fk, s.fk)

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

    def testGet(self):
        res = self.client_model.objects.get(pk=self.s1.pk)
        self.assertObjectsEqual(res, self.s1)

    def testCreate(self):
        c = self.client_model.objects.create(char_field='test', int_field=1)
        s = self.server_model.objects.get(pk=c.id)
        self.assertObjectsEqual(c, s)

    def testGetOrCreate(self):
        c, created = self.client_model.objects.get_or_create(
            char_field='first',
            defaults={'int_field': 1})
        self.assertFalse(created)
        self.assertIsInstance(c, self.client_model)
        self.assertObjectsEqual(c, self.s1)

    def testUpdateOrCreate(self):
        c, created = self.client_model.objects.update_or_create(
            char_field='first',
            defaults={'int_field': 10})
        self.assertFalse(created)
        self.assertIsInstance(c, self.client_model)
        s1 = self.server_model.objects.get(pk=self.s1.pk)
        self.assertEqual(s1.int_field, 10)
        self.assertObjectsEqual(c, s1)

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
        c2.id = None
        s3.id = None
        c3.id = None
        self.assertObjectsEqual(c2, s2)
        self.assertObjectsEqual(c3, s3)

    def testBulkCreateBatchSize(self):
        server_count = self.server_model.objects.count()
        c2 = self.client_model(char_field='2', int_field=1)
        c3 = self.client_model(char_field='3', int_field=1)
        ret = self.client_model.objects.bulk_create([c2, c3], batch_size=1)
        self.assertEqual(len(ret), 2)
        self.assertIsInstance(ret[0], self.client_model)
        self.assertObjectsEqual(ret[0], c2)
        self.assertEqual(self.server_model.objects.count(), server_count + 2)
        s2, s3 = self.server_model.objects.filter(pk__gt=self.s2.pk)
        s2.id = None
        c2.id = None
        s3.id = None
        c3.id = None
        self.assertObjectsEqual(c2, s2)
        self.assertObjectsEqual(c3, s3)

    def testCount(self):
        real = self.client_model.objects.count()
        expected = self.server_model.objects.count()
        self.assertEqual(real, expected)

    def testInBulk(self):
        cc = self.client_model.objects.in_bulk()
        ss = self.server_model.objects.in_bulk()
        self.assertIsInstance(cc, dict)
        self.assertEqual(len(cc), len(ss))
        self.assertSetEqual(set(cc.keys()), set(ss.keys()))
        c1 = cc[self.s1.pk]
        s1 = ss[self.s1.pk]
        self.assertObjectsEqual(c1, s1)

    def testIterator(self):
        client_iter = self.client_model.objects.filter(pk=self.s1.pk).iterator()
        server_iter = self.server_model.objects.filter(pk=self.s1.pk).iterator()
        self.assertObjectsEqual(next(client_iter), next(server_iter))
        with self.assertRaises(StopIteration):
            next(client_iter)

    def testLatest(self):
        c2 = self.client_model.objects.latest('dt_field')
        s2 = self.server_model.objects.latest('dt_field')
        self.assertObjectsEqual(c2, s2)

    def testEarliest(self):
        c1 = self.client_model.objects.earliest('dt_field')
        s1 = self.server_model.objects.earliest('dt_field')
        self.assertObjectsEqual(c1, s1)

    def testFirst(self):
        c1 = self.client_model.objects.order_by('char_field').first()
        s1 = self.server_model.objects.order_by('char_field').first()
        self.assertObjectsEqual(c1, s1)

    def testLast(self):
        c1 = self.client_model.objects.order_by('char_field').last()
        s1 = self.server_model.objects.order_by('char_field').last()
        self.assertObjectsEqual(c1, s1)

    def testAggregate(self):
        expected = self.server_model.objects.aggregate(c=models.Count('*'))
        real = self.client_model.objects.aggregate(c=models.Count('*'))
        self.assertDictEqual(expected, real)

    def testExists(self):
        exists = self.client_model.objects.filter(int_field=1).exists()
        self.assertIs(exists, True)

    def testUpdate(self):
        result = self.client_model.objects.filter(
            pk=self.s1.pk).update(int_field=100500)
        self.assertIs(result, 1)
        self.s1.refresh_from_db()
        self.assertEqual(self.s1.int_field, 100500)

    def testDelete(self):
        result = self.client_model.objects.filter(
            pk=self.s1.pk).delete()

        # Django-1.10 result is (total, {per_class})
        self.assertIsInstance(result, (tuple, list))
        self.assertEqual(result[0], 1)

        self.assertFalse(self.server_model.objects.filter(
            pk=self.s1.pk).exists())

    def testAsManager(self):
        m1 = self.client_model.objects.filter(int_field=2).as_manager()
        qs = self.client_model.objects.get_queryset()
        self.assertIsInstance(m1.get_queryset(), type(qs))

    # noinspection PyUnresolvedReferences
    def testModelSaveInsert(self):
        c = self.client_model(char_field='test', int_field=0)
        c.save()
        self.assertIsNotNone(c.id)
        s = self.server_model.objects.get(pk=c.id)
        self.assertObjectsEqual(c, s)

    # noinspection PyUnresolvedReferences
    def testModelSaveUpdate(self):
        c = self.client_model.objects.get(id=self.s1.id)
        c.int_field = 100500
        c.dt_field = now().replace(microsecond=123000)
        c.save()
        s = self.server_model.objects.get(pk=c.id)
        self.assertEqual(s.int_field, 100500)
        self.assertObjectsEqual(c, s)

    def testModelDelete(self):
        c = self.client_model.objects.get(id=self.s1.id)
        c.delete()
        self.assertFalse(self.server_model.objects.filter(id=c.id).exists())

    def assertQuerySetEqual(self, qs, expected):
        result = list(qs)
        self.assertEqual(len(result), len(expected))
        for real, exp in zip(result, expected):
            self.assertObjectsEqual(real, exp)
