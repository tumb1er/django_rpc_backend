# coding: utf-8
import celery

from django_rpc.celery.conf import settings


class RpcTaskBase(celery.Task):
    abstract = True


def nope(*args, **kwargs):
    pass


class RpcClient(object):
    clients = {}

    def __init__(self, config):
        app = celery.Celery()
        app.config_from_object(config)
        app.autodiscover_tasks(['django_rpc.celery'])
        self._app = app

        self.fetch = app.task(name='django_rpc.fetch', base=RpcTaskBase)(nope)

    def execute(self, app_label, name, trace):
        return self.fetch.delay(app_label, name, trace).get()

    @classmethod
    def from_db(cls, db):
        try:
            return cls.clients[db]
        except KeyError:
            cls.clients[db] = client = RpcClient(settings.DATABASES[db])
            return client
