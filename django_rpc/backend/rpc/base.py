# coding: utf-8
from django.db.backends.base import creation, features
from django.db.backends.dummy import base


class DatabaseWrapper(base.DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.ops = RpcOperations(self)
        self.creation = RpcCreation(self)
        self.features = RpcFeatures(self)

    def ensure_connection(self):
        pass


class RpcOperations(base.DatabaseOperations):
    compiler_module = "django_rpc.backend.rpc.compiler"

    def quote_name(self, name):
        return name


class RpcFeatures(features.BaseDatabaseFeatures):
    supports_transactions = False


class RpcCreation(creation.BaseDatabaseCreation):

    def create_test_db(self, *args, **kwargs):
        # NOOP, test using regular sphinx database.
        if self.connection.settings_dict.get('TEST_NAME'):
            # initialize connection database name
            test_name = self.connection.settings_dict['TEST_NAME']
            return test_name
        return self.connection.settings_dict['NAME']

    def destroy_test_db(self, *args, **kwargs):
        # NOOP, we created nothing, nothing to destroy.
        return