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

        class Serializer(serializers.ModelSerializer):
            class Meta:
                model = kwargs.get('model') or qs.model
                fields = kwargs.get('fields', '__all__')

        return Serializer(instance=qs, many=isinstance(qs, QuerySet)).data


class FetchTask(BaseRpcTask):

    def __call__(self, module_name, class_name, trace, fields='__all__'):
        fields = fields or '__all__'
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()
        for method, args, kwargs in trace:
            qs = getattr(qs, method)(*args, **kwargs)
            if not isinstance(qs, (QuerySet, Model)):
                return qs
        return self.serialize(qs, model=model, fields=fields)


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