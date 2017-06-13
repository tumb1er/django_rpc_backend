# coding: utf-8
import six

from django_rpc.celery.client import RpcClient
from django_rpc.models.manager import RpcManager

S_MUST_DEFINE_NON_EMPTY_ATTR = "%s.Rpc class must define non-empty %s attribute"

S_MUST_DEFINE_RPC_CLASS = "model %s must define Rpc class"


class RpcModelBase(type):

    # noinspection PyInitNewSignature
    def __new__(mcs, name, bases, attrs):
        mcs.init_rpc_meta(name, bases, attrs)
        new = super(RpcModelBase, mcs).__new__(mcs, name, bases, attrs)
        try:
            # Django manager already done this
            manager = getattr(new, 'objects')

            # Reconstruction RpcModel.objects for new class
            manager = type(manager)()
            manager.contribute_to_class(new, 'objects')
            setattr(new, 'objects', manager)
        except AttributeError:
            pass

        for k, v in attrs.items():
            if (hasattr(v, 'contribute_to_class') and not
                    getattr(v, 'model', None)):
                v.contribute_to_class(new, k)
        return new

    def __call__(cls, *args, **kwargs):
        obj = super(RpcModelBase, cls).__call__(*args)
        rpc = obj.Rpc
        if not hasattr(obj, rpc.pk_field):
            setattr(obj, rpc.pk_field, None)
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    @staticmethod
    def init_rpc_meta(name, bases, attrs):
        if not bases:
            return
        if attrs.get('_deferred'):
            return

        rpc = attrs.get('Rpc')
        assert rpc is not None, S_MUST_DEFINE_RPC_CLASS % name

        base_rpc = bases[0].Rpc
        for attr in 'db', 'pk_field':
            if not hasattr(rpc, attr):
                setattr(rpc, attr, getattr(base_rpc, attr))

        for attr in 'db', 'app_label', 'name':
            assert getattr(rpc, attr, None), \
                S_MUST_DEFINE_NON_EMPTY_ATTR % (name, attr)


class RpcModel(six.with_metaclass(RpcModelBase)):

    objects = RpcManager()

    class Rpc:
        db = 'rpc'
        app_label = None
        name = None
        pk_field = 'id'

    def save(self, force_insert=False, force_update=False, update_fields=None):
        if update_fields:
            force_update = True

        pk = getattr(self, self.Rpc.pk_field, None)
        if pk is None:
            force_insert = True

        assert not (force_insert and force_update), \
            "ambiguous force_update + force_insert"

        if update_fields:
            data = {k: v for k, v in self.__dict__.items()
                    if k in update_fields}
        else:
            data = self.__dict__.copy()

        if force_insert:
            obj = self.__class__.objects.create(**data)
            self.__dict__.update(obj.__dict__)
        else:
            opts = self.__class__.Rpc
            client = RpcClient.from_db(opts.db)
            qs = self.__class__.objects.filter(pk=pk)
            result = client.update(opts.app_label, opts.name, qs.rpc_trace,
                                   data, single=True)
            return result

    def delete(self):
        pk = getattr(self, self.Rpc.pk_field, None)
        assert pk is not None, "delete non-existing object"

        self.__class__.objects.filter(pk=pk).delete()
