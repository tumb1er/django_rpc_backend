# coding: utf-8

# Django DATABASES engine const
ENGINE = 'django_rpc.backend.rpc'

# Celery default settings
BROKER_URL = 'amqp://localhost/'
CELERY_RESULT_BACKEND = 'redis://localhost/'
CELERY_ACCEPT_CONTENT = ['json', 'x-rpc-json']
CELERY_TASK_SERIALIZER = 'x-rpc-json'
CELERY_RESULT_SERIALIZER = 'x-rpc-json'
