# coding: utf-8

import celery
from django.db.models import QuerySet, Model
from django.apps.registry import apps
from rest_framework import serializers


class FetchTask(celery.Task):
    abstract = True

    def __call__(self, module_name, class_name, trace, fields='__all__'):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()
        for method, args, kwargs in trace:
            qs = getattr(qs, method)(*args, **kwargs)
            if not isinstance(qs, (QuerySet, Model)):
                return qs
        return self.serialize(qs, model=model, fields=fields)

    def serialize(self, qs, **kwargs):

        class Serializer(serializers.ModelSerializer):
            class Meta:
                model = kwargs['model']
                fields = kwargs['fields']

        return Serializer(instance=qs, many=isinstance(qs, QuerySet)).data


@celery.task(base=FetchTask, bind=True, shared=True, name='django_rpc.fetch')
def fetch(*args, **kwargs):
    pass