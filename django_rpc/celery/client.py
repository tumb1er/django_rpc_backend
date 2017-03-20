# coding: utf-8
import celery

from django_rpc.celery.conf import settings


TASKS = (
    'django_rpc.fetch',
    'django_rpc.insert',
    'django_rpc.update',
    'django_rpc.get_or_create'
)


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
    def _update(self):
        return self._app.tasks['django_rpc.update']

    @property
    def _delete(self):
        return self._app.tasks['django_rpc.delete']

    @property
    def _get_or_create(self):
        return self._app.tasks['django_rpc.get_or_create']

    def fetch(self, app_label, name, trace, fields=None, extra_fields=None,
              exclude_fields=None, native=False):
        result = self._fetch.delay(
            app_label,
            name,
            trace,
            fields=fields,
            extra_fields=extra_fields,
            exclude_fields=exclude_fields,
            native=native)
        return result.get()

    def insert(self, app_label, name, objs, fields, return_id=False, raw=False):
        return self._insert.delay(app_label, name, objs, fields,
                                  return_id=return_id, raw=raw).get()

    def update(self, app_label, name, trace, updates):
        return self._update.delay(app_label, name, trace, updates).get()

    def delete(self, app_label, name, trace):
        return self._delete.delay(app_label, name, trace).get()

    def get_or_create(self, app_label, name, kwargs, update=False):
        return self._get_or_create.delay(app_label, name, kwargs,
                                         update=update).get()

    @classmethod
    def from_db(cls, db):
        try:
            return cls.clients[db]
        except KeyError:
            cls.clients[db] = client = RpcClient(settings.DATABASES[db])
            return client
