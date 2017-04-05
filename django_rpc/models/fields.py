# coding: utf-8


class ForeignKey(object):
    def __init__(self, model):
        self.model = model

    def contribute_to_class(self, klass, name):
        setattr(klass, name, ForwardFKDescriptor(self.model, name))


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