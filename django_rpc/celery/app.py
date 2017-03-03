# coding: utf-8
import os

import sys
sys.path.append('example_project')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_server'
import django
django.setup()


import celery

from .conf import config


celery = celery.Celery()
celery.config_from_object(config)
celery.autodiscover_tasks(['django_rpc.celery'])
