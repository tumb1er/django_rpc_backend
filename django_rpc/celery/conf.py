# coding: utf-8
import os

from copy import copy

from django_rpc.celery import defaults


def _merge_dict(conf):
    result = {}
    for k in dir(defaults):
        if k.upper() != k:
            continue
        default = getattr(defaults, k)
        result[k] = conf.get(k, default)
    result.update(conf)
    return result


class RpcSettings(object):

    def __init__(self, DATABASES=None):
        databases = {}
        for name, db in (DATABASES or {}).items():
            if db.get('ENGINE') != defaults.ENGINE:
                continue
            conf = _merge_dict(db)
            databases[name] = conf
        self.DATABASES = databases


if os.environ.get('DJANGO_SETTINGS_MODULE'):
    from django.conf import settings
    databases = settings.DATABASES
    config = _merge_dict(getattr(settings, 'DJANGO_RPC_CONF', {}))
else:
    databases = {'rpc': defaults.__dict__}

settings = RpcSettings(DATABASES=databases)



