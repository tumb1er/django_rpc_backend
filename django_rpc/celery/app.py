# coding: utf-8
import os

import sys
sys.path.append('example_project')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_server'
import django
django.setup()


from .conf import config

import celery


celery = celery.Celery(name="django_rpc.server")
celery.config_from_object(config)
celery.autodiscover_tasks(['django_rpc.celery'])
