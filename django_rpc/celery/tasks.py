# coding: utf-8

import celery
from django.db.models import QuerySet, Model, sql
from django.db import router
from django.apps.registry import apps
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


class FetchTask(BaseRpcTask):

    def __call__(self, module_name, class_name, trace, fields='__all__',
                 extra_fields=None, native=False):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()
        if not extra_fields:
            fields = fields or '__all__'
        elif fields:
            fields = fields + extra_fields
        else:
            fields = ([f.attname for f in model._meta.fields] +
                      list(extra_fields))
        for method, args, kwargs in trace:
            qs = getattr(qs, method)(*args, **kwargs)
            if not isinstance(qs, (QuerySet, Model)):
                return qs
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


class GetOrCreateTask(BaseRpcTask):

    def __call__(self, module_name, class_name, kwargs):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()
        obj, created = qs.get_or_create(**kwargs)

        data = self.serialize(obj, model=model)
        return data, created


@celery.task(base=FetchTask, bind=True, shared=True, name='django_rpc.fetch')
def fetch(*args, **kwargs):
    pass


@celery.task(base=InsertTask, bind=True, shared=True, name='django_rpc.insert')
def insert(*args, **kwargs):
    pass


@celery.task(base=GetOrCreateTask, bind=True, shared=True, name='django_rpc.get_or_create')
def get_or_create(*args, **kwargs):
    pass