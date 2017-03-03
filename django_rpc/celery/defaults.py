# coding: utf-8

DATABASES = {
    'rpc': {
        'BROKER_URL': 'amqp://localhost/',
        'CELERY_RESULT_BACKEND': 'redis://localhost/'
    }
}
