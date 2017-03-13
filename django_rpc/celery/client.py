# coding: utf-8
import celery
from copy import copy

from django_rpc.celery import defaults
from django_rpc.celery.conf import settings


def task(app, name):
    def nope(*args, **kwargs):
        pass

    return app.task(name=name)(nope)


class RpcClient(object):
    clients = {}

    def __init__(self, config):
        app = celery.Celery()
        app.config_from_object(config)
        app.autodiscover_tasks(['django_rpc.celery'])
        for name in 'django_rpc.fetch', 'django_rpc.insert':
            if name not in app.tasks:
                task(app, name)
        self._app = app

    @property
    def _insert(self):
        return self._app.tasks['django_rpc.insert']

    @property
    def _fetch(self):
        return self._app.tasks['django_rpc.fetch']

    def fetch(self, app_label, name, trace):
        return self._fetch.delay(app_label, name, trace).get()

    def insert(self, app_label, name, objs, fields, return_id=False, raw=False):
        return self._insert.delay(app_label, name, objs, fields,
                                  return_id=return_id, raw=raw).get()

    @classmethod
    def from_db(cls, db):
        try:
            return cls.clients[db]
        except KeyError:
            cls.clients[db] = client = RpcClient(settings.DATABASES[db])
            return client
