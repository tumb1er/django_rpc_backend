from distutils.core import setup

setup(
    name='django_rpc_backend',
    version='0.0.1',
    packages=[
        'django_rpc',
        'django_rpc.backend',
        'django_rpc.backend.rpc',
        'django_rpc.celery',
        'django_rpc.models'
    ],
    url='https://github.com/tumb1er/django_rpc_backend',
    license='Beerware',
    author='Tumbler',
    author_email='zimbler@gmail.com',
    description='Django RPC database backend',
    requires=[
        'pytz',
        'celery',
        'django',
        'six',
        'jsonpickle'],
    test_requres=['mock']
)
