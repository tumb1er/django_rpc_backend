# coding: utf-8

import celery
from django.apps.registry import apps
from django.db.models import QuerySet, Model
from rest_framework import serializers


class BaseRpcTask(celery.Task):
    abstract = True

    @staticmethod
    def serialize(qs, **kwargs):

        extra_fields = kwargs.get('extra_fields', ())

        class Meta:
            model = kwargs.get('model') or qs.model
            fields = kwargs.get('fields', '__all__')

        attrs = {'Meta': Meta}
        attrs.update({k: serializers.ReadOnlyField() for k in extra_fields})

        serializer_class = type("Serializer",
                                (serializers.ModelSerializer,),
                                attrs)

        return serializer_class(instance=qs, many=isinstance(qs, QuerySet)).data

    def trace_queryset(self, qs, trace):
        for method, args, kwargs in trace:
            qs = getattr(qs, method)(*args, **kwargs)
            if not isinstance(qs, (QuerySet, Model)):
                break
        return qs


class FetchTask(BaseRpcTask):

    def __call__(self, module_name, class_name, trace, fields=None,
                 extra_fields=None, exclude_fields=None, native=False):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()

        exclude_fields = list(exclude_fields or ())
        extra_fields = list(extra_fields or ())
        fields = list(fields or [])

        if extra_fields or exclude_fields or not fields:
            fields = ([f.attname for f in model._meta.fields] +
                      list(extra_fields))

        fields = [f for f in fields + extra_fields
                  if f not in exclude_fields] or '__all__'

        qs = self.trace_queryset(qs, trace)
        if native:
            return qs
        return self.serialize(qs, model=model, fields=fields,
                              extra_fields=extra_fields)


class InsertTask(BaseRpcTask):

    def __call__(self, module_name, class_name, rpc_data, rpc_fields,
                 return_id=False, raw=False):

        class Serializer(serializers.ModelSerializer):
            class Meta:
                fields = rpc_fields
                model = apps.get_model(module_name, class_name)

        s = Serializer(data=rpc_data, many=True)
        if s.is_valid(raise_exception=True):
            result = s.save()
            if return_id:
                return result[0].pk


class UpdateTask(BaseRpcTask):

    def __call__(self, module_name, class_name, trace, updates):
        model = apps.get_model(module_name, class_name)

        qs = model.objects.get_queryset()
        qs = self.trace_queryset(qs, trace)
        return qs.update(**updates)


class GetOrCreateTask(BaseRpcTask):

    def __call__(self, module_name, class_name, kwargs, update=False):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()
        if update:
            obj, created = qs.update_or_create(**kwargs)
        else:
            obj, created = qs.get_or_create(**kwargs)

        data = self.serialize(obj, model=model)
        return data, created


@celery.task(base=FetchTask, bind=True, shared=True, name='django_rpc.fetch')
def fetch(*args, **kwargs):
    pass


@celery.task(base=InsertTask, bind=True, shared=True, name='django_rpc.insert')
def insert(*args, **kwargs):
    pass


@celery.task(base=UpdateTask, bind=True, shared=True, name='django_rpc.update')
def update(*args, **kwargs):
    pass


@celery.task(base=GetOrCreateTask, bind=True, shared=True,
             name='django_rpc.get_or_create')
def get_or_create(*args, **kwargs):
    pass