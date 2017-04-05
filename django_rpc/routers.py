# coding: utf-8
from django.conf import settings

RPC_DATABASE_NAME = getattr(settings, 'RPC_DATABASE_NAME', 'rpc')


class RpcRouter(object):
    """
    Routes database operations for rpc models to corresponding rpc connections.
    """

    @staticmethod
    def is_rpc_model(model_or_obj):
        from django_rpc.models import DjangoRpcModelBase, DjangoRpcModel
        if type(model_or_obj) is not DjangoRpcModelBase:
            model = model_or_obj.__class__
        else:
            model = model_or_obj
        is_rpc = (issubclass(model, DjangoRpcModel) or
                  type(model) is DjangoRpcModelBase)
        return is_rpc

    # noinspection PyUnusedLocal
    def db_for_read(self, model, **kwargs):
        if self.is_rpc_model(model):
            return RPC_DATABASE_NAME

    # noinspection PyUnusedLocal
    def db_for_write(self, model, **kwargs):
        if self.is_rpc_model(model):
            return RPC_DATABASE_NAME

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def allow_relation(self, obj1, obj2, **kwargs):
        # Allow all relations...
        return True

    # noinspection PyUnusedLocal
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == RPC_DATABASE_NAME:
            return False
        if self.is_rpc_model(hints.get('model')):
            return False
        return None
