# coding: utf-8
import six

from django_rpc.models.manager import RpcManager

S_MUST_DEFINE_NON_EMPTY_ATTR = "%s.Rpc class must define non-empty %s attribute"

S_MUST_DEFINE_RPC_CLASS = "model %s must define Rpc class"


class RpcModelBase(type):

    # noinspection PyInitNewSignature
    def __new__(cls, name, bases, attrs):
        cls.init_rpc_meta(name, bases, attrs)
        new = super(RpcModelBase, cls).__new__(cls, name, bases, attrs)
        try:
            # Django manager already done this
            manager = getattr(new, 'objects')
            manager.contribute_to_class(new, 'objects')
        except AttributeError:
            pass
        return new

    @staticmethod
    def init_rpc_meta(name, bases, attrs):
        if not bases:
            return
        rpc = attrs.get('Rpc')
        assert rpc is not None, S_MUST_DEFINE_RPC_CLASS % name

        if not hasattr(rpc, 'db'):
            rpc.db = 'rpc'

        for attr in 'db', 'app_label', 'name':
            assert getattr(rpc, attr, None), \
                S_MUST_DEFINE_NON_EMPTY_ATTR % (name, attr)


class RpcModel(six.with_metaclass(RpcModelBase)):

    objects = RpcManager()

    class Rpc:
        db = 'rpc'
        app_label = None
        name = None
