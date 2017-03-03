# coding: utf-8
import os

from django_rpc.celery import defaults


class RpcSettings(object):

    def __init__(self, **conf):
        self.__dict__.update(conf)


if os.environ.get('DJANGO_SETTINGS_MODULE'):
    from django.conf import settings
else:
    settings = defaults

settings = RpcSettings(DATABASES=settings.DATABASES)
