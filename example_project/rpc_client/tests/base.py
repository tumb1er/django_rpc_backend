# coding: utf-8
from unittest import TestCase

import pytz
from celery import Task
from collections import defaultdict
from django.db import models
from django.db.models import Count
from django.db.models.signals import pre_save, post_save, pre_delete, \
    post_delete
from django.utils.timezone import now
from mock import mock

from django_rpc.celery import codecs, app


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
        p = mock.patch('django_rpc.celery.client.RpcClient._app',
                       new_callable=mock.PropertyMock(return_value=app.celery))
        cls._celery_app_patcher = p
        p.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for p in (cls._apply_async_patcher, cls._celery_app_patcher):
            if hasattr(p, 'is_local'):
                p.stop()


class QuerySetTestsMixin(TestCase):
    client_model = None
    server_model = None
    fk_model = None
    fk_client_model = None
    """ 
    :type client_model: django_rpc.models.RpcModel
    :type server_model: rpc_server.models.ServerModel
    :type fk_model: rpc_server.models.FKModel
    :type fk_client_model: django_rpc.models.RpcModel
    """

    def assertObjectsEqual(self, o1, o2):
        d1 = o1.__dict__.copy()
        for f in '_state', '_fk_cache':
            d1.pop(f, None)
        d2 = o2.__dict__.copy()
        for f in '_state', '_fk_cache':
            d2.pop(f, None)
        self.assertDictEqual(d1, d2)

    def assertQuerySetEqual(self, qs, expected):
        result = list(qs)
        self.assertEqual(len(result), len(expected))
        for real, exp in zip(result, expected):
            self.assertObjectsEqual(real, exp)

    def setUp(self):
        super(QuerySetTestsMixin, self).setUp()
        self.s1 = self.server_model.objects.get(pk=1)
        self.s2 = self.server_model.objects.get(pk=2)
        self.signals = defaultdict(list)
        self.signal_model = self.server_model

    def testFilter(self):
        qs = self.client_model.objects.filter(pk=self.s1.pk)
        self.assertQuerySetEqual(qs, [self.s1])

    def testExclude(self):
        qs = self.client_model.objects.exclude(pk=self.s1.pk)
        self.assertQuerySetEqual(qs, [self.s2])

    def testAnnotate(self):
        qs = self.fk_client_model.objects.annotate(cs=Count('servermodel'))
        ss = self.fk_model.objects.annotate(cs=Count('servermodel'))
        self.assertQuerySetEqual(qs, ss)

    def testOrderBy(self):
        qs = self.client_model.objects.order_by('-pk')
        self.assertQuerySetEqual(qs, [self.s2, self.s1])

    def testReverse(self):
        qs = self.client_model.objects.order_by('pk').reverse()
        self.assertQuerySetEqual(qs, [self.s2, self.s1])

    def testDistinct(self):
        data = list(self.client_model.objects.values('int_field').distinct())
        expected = list(self.server_model.objects.values(
            'int_field').distinct())
        self.assertEqual(len(data), len(expected))
        for d, e in zip(data, expected):
            self.assertDictEqual(d, e)

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
        with self.mock_celery_task() as apply:
            qs = self.client_model.objects.none()
            self.assertListEqual(list(qs), [])
        self.assertFalse(apply.called)

    def testAll(self):
        qs = self.client_model.objects.all()
        expected = self.server_model.objects.all()
        self.assertQuerySetEqual(qs, expected)

    def testSelectRelated(self):
        qs = self.client_model.objects.filter(pk=1).select_related('fk')
        c = qs[0]
        s = self.server_model.objects.filter(pk=1).select_related('fk')[0]
        self.assertTrue(hasattr(c, '_fk_cache'))
        self.assertObjectsEqual(c.fk, s.fk)

    def testClearSelectRelated(self):
        qs = self.client_model.objects.filter(pk=1)
        c = qs[0]
        self.assertFalse(hasattr(c, '_fk_cache'))
        qs = self.client_model.objects.filter(pk=1).select_related('fk')
        qs = qs.select_related(None)
        c = qs[0]
        self.assertFalse(hasattr(c, '_fk_cache'))

    def testPrefetchRelated(self):
        ss = self.fk_model.objects.filter(pk=1)
        qs = self.fk_client_model.objects.filter(pk=1)
        self.assertFalse(hasattr(ss[0], '_prefetched_objects_cache'))
        self.assertFalse(hasattr(qs[0], '_prefetched_objects_cache'))

        ss = ss.prefetch_related('servermodel_set')
        qs = qs.prefetch_related('servermodel_set')

        d = qs[0]
        e = ss[0]
        self.assertTrue(hasattr(e, '_prefetched_objects_cache'))
        self.assertIs(e._prefetched_objects_cache['servermodel'].model,
                      self.server_model)
        self.assertTrue(hasattr(d, '_prefetched_objects_cache'))
        self.assertIs(d._prefetched_objects_cache['servermodel'].model,
                      self.client_model)

        del d._prefetched_objects_cache
        del e._prefetched_objects_cache
        self.assertObjectsEqual(d, e)

    def testClearPrefetchRelated(self):
        qs = self.fk_client_model.objects.filter(pk=1)
        c = qs[0]
        self.assertFalse(hasattr(c, '_prefetched_objects_cache'))
        qs = qs.prefetch_related('servermodel_set')
        qs = qs.prefetch_related(None)
        c = qs[0]
        self.assertFalse(hasattr(c, '_prefetched_objects_cache'))

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
        self.connect_signals()
        c = self.client_model.objects.create(char_field='test', int_field=1)
        self.disconnect_signals()
        s = self.server_model.objects.get(pk=c.id)
        self.assertObjectsEqual(c, s)
        self.assertTrue(self.signals['pre_save'])
        self.assertTrue(self.signals['post_save'])

    def testGetOrCreate(self):
        self.s1.delete()
        self.connect_signals()
        c, created = self.client_model.objects.get_or_create(
            char_field='first',
            defaults={'int_field': 1})
        self.disconnect_signals()
        self.assertTrue(created)
        self.assertIsInstance(c, self.client_model)
        self.s1.id = c.id
        self.s1.refresh_from_db()
        self.assertObjectsEqual(c, self.s1)
        self.assertTrue(self.signals['pre_save'])
        self.assertTrue(self.signals['post_save'])

    def testGetOrCreateExists(self):
        c, created = self.client_model.objects.get_or_create(
            char_field='first',
            defaults={'int_field': 1})
        self.assertFalse(created)
        self.assertIsInstance(c, self.client_model)
        self.assertObjectsEqual(c, self.s1)

    def testUpdateOrCreate(self):
        self.s1.delete()
        self.connect_signals()
        c, created = self.client_model.objects.update_or_create(
            char_field='first',
            defaults={'int_field': 10})
        self.disconnect_signals()
        self.assertTrue(created)
        self.assertIsInstance(c, self.client_model)
        self.s1.id = c.id
        self.s1.refresh_from_db()
        self.assertEqual(self.s1.int_field, 10)
        self.assertObjectsEqual(c, self.s1)
        self.assertTrue(self.signals['pre_save'])
        self.assertTrue(self.signals['post_save'])

    def testUpdateOrCreateExists(self):
        self.connect_signals()
        c, created = self.client_model.objects.update_or_create(
            char_field='first',
            defaults={'int_field': 10})
        self.disconnect_signals()
        self.assertFalse(created)
        self.assertIsInstance(c, self.client_model)
        s1 = self.server_model.objects.get(pk=self.s1.pk)
        self.assertEqual(s1.int_field, 10)
        self.assertObjectsEqual(c, s1)
        self.assertTrue(self.signals['pre_save'])
        self.assertTrue(self.signals['post_save'])

    def testBulkCreate(self):
        server_count = self.server_model.objects.count()
        c2 = self.client_model(char_field='2', int_field=1)
        c3 = self.client_model(char_field='3', int_field=1)
        self.connect_signals()
        ret = self.client_model.objects.bulk_create([c2, c3])
        self.disconnect_signals()
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
        self.assertFalse(self.signals['pre_save'])
        self.assertFalse(self.signals['post_save'])

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
        self.connect_signals()
        result = self.client_model.objects.filter(
            pk=self.s1.pk).update(int_field=100500)
        self.disconnect_signals()
        self.assertIs(result, 1)
        self.s1.refresh_from_db()
        self.assertEqual(self.s1.int_field, 100500)
        self.assertFalse(self.signals['pre_save'])
        self.assertFalse(self.signals['post_save'])

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

    def testModelSaveInsert(self):
        c = self.client_model(char_field='test', int_field=0)
        self.connect_signals()
        c.save()
        self.disconnect_signals()
        self.assertIsNotNone(c.id)
        s = self.server_model.objects.get(pk=c.id)
        self.assertObjectsEqual(c, s)
        self.assertTrue(self.signals['pre_save'])
        self.assertTrue(self.signals['post_save'])

    def testModelSaveUpdate(self):
        c = self.client_model.objects.get(id=self.s1.id)
        c.int_field = 100500
        c.dt_field = now().replace(microsecond=123000)
        self.connect_signals()
        c.save()
        self.disconnect_signals()
        s = self.server_model.objects.get(pk=c.id)
        self.assertEqual(s.int_field, 100500)
        self.assertObjectsEqual(c, s)
        self.assertTrue(self.signals['pre_save'])
        self.assertTrue(self.signals['post_save'])

    def testModelDelete(self):
        c = self.client_model.objects.get(id=self.s1.id)
        self.connect_signals()
        c.delete()
        self.disconnect_signals()
        self.assertFalse(self.server_model.objects.filter(id=c.id).exists())
        self.assertTrue(self.signals['pre_delete'])
        self.assertTrue(self.signals['post_delete'])

    def testGetItem(self):
        self.clone(self.s1, 5)

        d = self.client_model.objects.all()[2]
        e = self.server_model.objects.all()[2]
        self.assertObjectsEqual(d, e)

    def testSlice(self):
        self.clone(self.s1, 5)
        with self.mock_celery_task() as apply:
            d = self.client_model.objects.all()[2: 5]
        self.assertFalse(apply.called)
        e = self.server_model.objects.all()[2: 5]
        self.assertQuerySetEqual(d, e)

    def testSlicedQueryset(self):
        self.clone(self.s1, 5)
        with self.mock_celery_task() as apply:
            d = self.client_model.objects.all()[2: 5][1: 2]
        self.assertFalse(apply.called)
        e = self.server_model.objects.all()[2: 5][1: 2]
        self.assertQuerySetEqual(list(d), list(e))

    def testLen(self):
        self.clone(self.s1, 5)
        d = len(self.client_model.objects.all())
        e = len(self.server_model.objects.all())
        self.assertEqual(d, e)

    def testOneToManyFK(self):
        d_fk = self.fk_client_model.objects.first()
        e_fk = self.fk_model.objects.first()
        self.assertObjectsEqual(d_fk, e_fk)
        self.assertQuerySetEqual(d_fk.servermodel_set.all(),
                                 e_fk.servermodel_set.all())

    def testFKInstance(self):
        c = self.client_model.objects.get(pk=self.s1.pk)
        d_fk = c.fk
        e_fk = self.s1.fk
        self.assertObjectsEqual(d_fk, e_fk)

    def testFilterByFK(self):
        c = self.client_model.objects.get(pk=self.s1.pk)
        d_fk = c.fk
        e_fk = self.s1.fk
        self.assertQuerySetEqual(self.client_model.objects.filter(fk=d_fk),
                                 self.server_model.objects.filter(fk=e_fk))

    def clone(self, obj, count):
        kw = obj.__dict__.copy()
        del kw['id']
        del kw['_state']
        s = type(obj)(**kw)
        self.server_model.objects.bulk_create([s] * count)

    def record_pre_save(self, **kwargs):
        self.signals['pre_save'].append(kwargs)

    def record_post_save(self, **kwargs):
        self.signals['post_save'].append(kwargs)

    def record_pre_del(self, **kwargs):
        self.signals['pre_delete'].append(kwargs)

    def record_post_del(self, **kwargs):
        self.signals['post_delete'].append(kwargs)

    def connect_signals(self):
        pre_save.connect(self.record_pre_save, sender=self.signal_model)
        post_save.connect(self.record_post_save, sender=self.signal_model)
        pre_delete.connect(self.record_pre_del, sender=self.signal_model)
        post_delete.connect(self.record_post_del, sender=self.signal_model)

    def disconnect_signals(self):
        pre_save.disconnect(self.record_pre_save, sender=self.signal_model)
        post_save.disconnect(self.record_post_save, sender=self.signal_model)
        pre_delete.disconnect(self.record_pre_del, sender=self.signal_model)
        post_delete.disconnect(self.record_post_del, sender=self.signal_model)

    @staticmethod
    def mock_celery_task():
        return mock.patch('celery.app.task.Task.apply_async')
