# coding: utf-8

import celery
from django.db.models import QuerySet, Model, sql
from django.db import router
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


class InsertTask(celery.Task):
    abstract = True

    def __call__(self, module_name, class_name, objs, fields, return_id=False,
                 raw=False):
        model = apps.get_model(module_name, class_name)
        using = router.db_for_write(model)
        query = sql.InsertQuery(model)
        query.insert_values(fields, objs, raw=raw)
        return query.get_compiler(using=using).execute_sql(return_id)


@celery.task(base=FetchTask, bind=True, shared=True, name='django_rpc.fetch')
def fetch(*args, **kwargs):
    pass


@celery.task(base=InsertTask, bind=True, shared=True, name='django_rpc.insert')
def insert(*args, **kwargs):
    pass
