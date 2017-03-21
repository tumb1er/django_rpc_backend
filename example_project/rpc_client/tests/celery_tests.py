# coding: utf-8
from unittest import skipIf

from celery.bin.celery import CeleryCommand
from django.conf import settings
from django.test import TestCase
from multiprocessing import Process

from django_rpc.celery.app import celery
from django_rpc.celery.client import RpcClient
from rpc_client.tests import base, NativeModel
from rpc_server.models import ServerModel


def use_file_sqlite():
    try:
        name = settings.DATABASES['default']['TEST']['NAME']
    except KeyError:
        return False
    return name and name.endswith('.sqlite3')


@skipIf(not use_file_sqlite(),
        reason=':memory: SQLite database is not working with multiprocessing')
class NativeCeleryTestCase(base.QuerySetTestsMixin, base.BaseRpcTestCase,
                           TestCase):
    client_model = NativeModel
    server_model = ServerModel
    fixtures = ['tests.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._apply_async_patcher.stop()
        cmd = 'celery worker -c 1 -A django_rpc.celery.app --loglevel=DEBUG'
        cls.celery = Process(target=start_celery, args=[cmd.split(' ')])
        cls.celery.start()
        celery.conf.update(CELERY_ALWAYS_EAGER=False)
        cls.rpc_client = RpcClient.from_db('rpc')
        conf = cls.rpc_client._app.conf
        cls.eager = conf['CELERY_ALWAYS_EAGER']
        conf['CELERY_ALWAYS_EAGER'] = False

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.celery.terminate()
        cls.rpc_client._app.conf['CELERY_ALWAYS_EAGER'] = cls.eager


def start_celery(argv):
    cmd = CeleryCommand()
    cmd.maybe_patch_concurrency()
    cmd.execute_from_commandline(argv)
