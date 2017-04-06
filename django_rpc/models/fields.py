# coding: utf-8


class ForeignKey(object):
    def __init__(self, model):
        self.remote_model = model
        self.model = None

    def contribute_to_class(self, model, name):
        self.model = model
        setattr(model, name, ForwardFKDescriptor(self.remote_model, name))
        model_name = model.Rpc.name.lower()
        descriptor_name = '%s_set' % model_name
        setattr(self.remote_model, descriptor_name,
                ReverseFKDescriptor(model, model_name, self.remote_model))


class ReverseFKDescriptor(object):
    def __init__(self, model, name, remote_model):
        self.model = model
        self.name = name
        self.fk_name = remote_model.Rpc.pk_field

    def __get__(self, instance, owner):
        if not instance:
            return self
        try:
            # noinspection PyProtectedMember
            return instance._prefetched_objects_cache[self.name]
        except (AttributeError, KeyError):
            return self.model.objects.filter(pk=getattr(instance, self.fk_name))

    def __set__(self, instance, value):
        raise NotImplementedError("Setting reverse descriptor not allowed")

    def set(self, instance, data):
        qs = self.model.objects.get_queryset()
        if not hasattr(instance, '_prefetched_objects_cache'):
            instance._prefetched_objects_cache = cache = {}
        else:
            cache = instance._prefetched_objects_cache

        qs._result_cache = [qs.instantiate(i) for i in data]
        cache[self.name] = qs


class ForwardFKDescriptor(object):
    def __init__(self, model, name):
        self.fk_name = '%s_id' % name
        self.cache_name = '_%s_cache' % name
        self.model = model
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return self
        try:
            obj = getattr(instance, self.cache_name)
        except AttributeError:
            fk = getattr(instance, self.fk_name, None)
            if fk is None:
                return None
            obj = self.model.objects.get(pk=fk)
            setattr(instance, self.cache_name, obj)
        return obj

    def __set__(self, instance, value):
        setattr(instance, self.cache_name, value)
        if value is None:
            fk = None
        else:
            fk = getattr(value, value.Rpc.pk_field)
        setattr(instance, self.fk_name, fk)

    def set(self, instance, data):
        qs = self.model.objects.get_queryset()
        self.__set__(instance, qs.instantiate(data))
