# coding: utf-8
import celery

from django_rpc.celery.conf import settings


TASKS = 'django_rpc.fetch', 'django_rpc.insert', 'django_rpc.get_or_create'


def task(app, name):
    # noinspection PyUnusedLocal
    def nope(*args, **kwargs):
        pass

    return app.task(name=name)(nope)


class RpcClient(object):
    clients = {}

    def __init__(self, config):
        app = celery.Celery()
        app.config_from_object(config)
        app.autodiscover_tasks(['django_rpc.celery'])
        for name in set(TASKS) - set(app.tasks.keys()):
            task(app, name)
        self._app = app

    @property
    def _insert(self):
        return self._app.tasks['django_rpc.insert']

    @property
    def _fetch(self):
        return self._app.tasks['django_rpc.fetch']

    @property
    def _get_or_create(self):
        return self._app.tasks['django_rpc.get_or_create']

    def fetch(self, app_label, name, trace, fields=None, extra_fields=None,
              native=False):
        return self._fetch.delay(app_label, name, trace, fields=fields,
                                 extra_fields=extra_fields, native=native).get()

    def insert(self, app_label, name, objs, fields, return_id=False, raw=False):
        return self._insert.delay(app_label, name, objs, fields,
                                  return_id=return_id, raw=raw).get()

    def get_or_create(self, app_label, name, **kwargs):
        return self._get_or_create.delay(app_label, name, kwargs).get()

    @classmethod
    def from_db(cls, db):
        try:
            return cls.clients[db]
        except KeyError:
            cls.clients[db] = client = RpcClient(settings.DATABASES[db])
            return client
