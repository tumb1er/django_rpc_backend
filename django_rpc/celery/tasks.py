# coding: utf-8

import celery
from django.apps.registry import apps
from django.db.models import QuerySet, Model
from rest_framework import serializers


# noinspection PyAbstractClass
class BaseRpcTask(celery.Task):
    abstract = True

    def serialize(self, qs, **kwargs):

        extra_fields = kwargs.get('extra_fields', ())

        class Meta:
            model = kwargs.get('model') or qs.model
            fields = kwargs.get('fields', '__all__')

        if Meta.fields == '__all__':
            # fix related objects attribute names
            Meta.fields = self.get_fields(Meta.model)

        attrs = {'Meta': Meta}
        attrs.update({k: serializers.ReadOnlyField() for k in extra_fields})

        serializer_class = type("Serializer",
                                (serializers.ModelSerializer,),
                                attrs)

        return serializer_class(instance=qs, many=isinstance(qs, QuerySet)).data

    @staticmethod
    def get_fields(model):
        # noinspection PyProtectedMember
        return [f.attname for f in model._meta.fields]

    @staticmethod
    def trace_queryset(qs, trace):
        for method, args, kwargs in trace:
            qs = getattr(qs, method)(*args, **kwargs)
            if not isinstance(qs, (QuerySet, Model)):
                break
        return qs


# noinspection PyAbstractClass
class FetchTask(BaseRpcTask):

    def __call__(self, module_name, class_name, trace, fields=None,
                 extra_fields=None, exclude_fields=None, native=False):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()

        exclude_fields = list(exclude_fields or ())
        extra_fields = list(extra_fields or ())
        fields = list(fields or [])

        if extra_fields or exclude_fields or not fields:
            fields = self.get_fields(model) + list(extra_fields)

        fields = [f for f in fields + extra_fields
                  if f not in exclude_fields] or '__all__'

        qs = self.trace_queryset(qs, trace)
        if native:
            if isinstance(qs, QuerySet):
                return list(qs)
            return qs
        return self.serialize(qs, model=model, fields=fields,
                              extra_fields=extra_fields)


# noinspection PyAbstractClass
class InsertTask(BaseRpcTask):

    def __call__(self, module_name, class_name, rpc_data, rpc_fields,
                 return_id=False, raw=False):

        class Serializer(serializers.ModelSerializer):
            class Meta:
                model = apps.get_model(module_name, class_name)
                fields = self.get_fields(model)

        s = Serializer(data=rpc_data, many=True)
        if s.is_valid(raise_exception=True):
            result = s.save()
            if return_id:
                return result[0].pk
            return s.data


# noinspection PyAbstractClass
class UpdateTask(BaseRpcTask):

    def __call__(self, module_name, class_name, trace, updates):
        model = apps.get_model(module_name, class_name)

        qs = model.objects.get_queryset()
        qs = self.trace_queryset(qs, trace)
        return qs.update(**updates)


# noinspection PyAbstractClass
class DeleteTask(BaseRpcTask):

    def __call__(self, module_name, class_name, trace):
        model = apps.get_model(module_name, class_name)

        qs = model.objects.get_queryset()
        qs = self.trace_queryset(qs, trace)
        return qs.delete()


# noinspection PyAbstractClass
class GetOrCreateTask(BaseRpcTask):

    # noinspection PyShadowingNames
    def __call__(self, module_name, class_name, kwargs, update=False):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()
        if update:
            obj, created = qs.update_or_create(**kwargs)
        else:
            obj, created = qs.get_or_create(**kwargs)

        data = self.serialize(obj, model=model)
        return data, created


# noinspection PyUnusedLocal
@celery.task(base=FetchTask, bind=True, shared=True, name='django_rpc.fetch')
def fetch(*args, **kwargs):
    pass


# noinspection PyUnusedLocal
@celery.task(base=InsertTask, bind=True, shared=True, name='django_rpc.insert')
def insert(*args, **kwargs):
    pass


# noinspection PyUnusedLocal
@celery.task(base=UpdateTask, bind=True, shared=True, name='django_rpc.update')
def update(*args, **kwargs):
    pass


# noinspection PyUnusedLocal
@celery.task(base=DeleteTask, bind=True, shared=True, name='django_rpc.delete')
def delete(*args, **kwargs):
    pass


# noinspection PyUnusedLocal
@celery.task(base=GetOrCreateTask, bind=True, shared=True,
             name='django_rpc.get_or_create')
def get_or_create(*args, **kwargs):
    pass
