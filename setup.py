from setuptools import setup

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
    install_requires=[
        'pytz',
        'celery',
        'django',
        'six',
        'jsonpickle',
        'djangorestframework'],
    tests_require=['mock', 'redis']
)
