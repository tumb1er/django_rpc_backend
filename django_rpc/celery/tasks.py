# coding: utf-8

from django.apps.registry import apps
from django.db.models import QuerySet, Model
from django.core.exceptions import FieldDoesNotExist
import celery
from django_rpc.celery.app import celery as celery_app
from rest_framework import serializers


class BaseRpcTask(celery_app.Task):
    abstract = True

    def serialize(self, qs, **kwargs):

        extra = kwargs.get('extra_fields', ())

        model = kwargs.get('model') or qs.model
        fields = kwargs.get('fields', '__all__')

        if fields == '__all__':
            # fix related objects attribute names
            fields = self.get_fields(model)

        serializer_class = self.get_serializer_class(model, fields, extra)

        return serializer_class(instance=qs, many=isinstance(qs, QuerySet)).data

    # noinspection PyProtectedMember
    def get_serializer_class(self, model, fields=None, extra_fields=()):
        fields = fields or self.get_fields(model)
        # noinspection PyPep8Naming
        Meta = type('Meta', (), {'model': model, 'fields': fields})
        attrs = {'Meta': Meta}
        opts = model._meta
        for k in list(fields) + list(extra_fields):
            try:
                descriptor = getattr(model, k)
            except AttributeError:
                try:
                    f = opts.get_field(k)
                    if f.name != k:
                        attrs[k] = serializers.ReadOnlyField()
                except FieldDoesNotExist:
                    attrs[k] = serializers.ReadOnlyField()
            else:
                f = descriptor.field
                if not f.is_relation:
                    attrs[k] = serializers.ReadOnlyField()
                else:
                    many = hasattr(descriptor, 'rel')
                    model = f.model if many else f.related_model
                    fields = self.get_fields(model)

                    # noinspection PyPep8Naming
                    NestedSerializer = self.get_serializer_class(model, fields)
                    nested = NestedSerializer(many=many, required=not f.blank, allow_null=f.null)
                    attrs[k] = nested
        serializer_class = type("Serializer",
                                (serializers.ModelSerializer,),
                                attrs)
        return serializer_class

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


class FetchTask(BaseRpcTask):
    name = 'django_rpc.fetch'

    def run(self, module_name, class_name, trace, fields=None,
            extra_fields=None, exclude_fields=None, native=False,
            limits=(0, None)):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()

        exclude_fields = list(exclude_fields or ())
        extra_fields = list(extra_fields or ())
        fields = list(fields or [])

        if extra_fields or exclude_fields or not fields:
            fields = self.get_fields(model)

        fields = [f for f in fields + extra_fields
                  if f not in exclude_fields] or '__all__'

        qs = self.trace_queryset(qs, trace)
        if native:
            if isinstance(qs, QuerySet):
                return list(qs)
            return qs

        if tuple(limits) != (0, None):
            start, stop = limits
            qs = qs[slice(start, stop)]
        return self.serialize(qs, model=model, fields=fields,
                              extra_fields=extra_fields)


class InsertTask(BaseRpcTask):
    name = 'django_rpc.insert'

    def run(self, module_name, class_name, rpc_data, return_id=False):

        model = apps.get_model(module_name, class_name)

        serializer_class = self.get_serializer_class(model)

        many = len(rpc_data) > 1
        data = rpc_data if many else rpc_data[0]
        s = serializer_class(data=data, many=many)
        s.is_valid(raise_exception=True)

        if many:
            objects = [model(**item) for item in s.validated_data]
            model.objects.bulk_create(objects)
            s = serializer_class(instance=objects, many=True)
        else:
            result = s.save()
            if return_id:
                return result.pk
        return s.data if many else [s.data]


class UpdateTask(BaseRpcTask):
    name = 'django_rpc.update'

    def run(self, module_name, class_name, trace, updates, single=False):
        model = apps.get_model(module_name, class_name)
        # noinspection PyProtectedMember
        pk_name = model._meta.pk.attname
        updates.pop(pk_name, None)
        qs = model.objects.get_queryset()
        qs = self.trace_queryset(qs, trace)
        if single:
            instance = qs.get()
            for k, v in updates.items():
                setattr(instance, k, v)
            instance.save(update_fields=list(updates.keys()))
            return 1
        return qs.update(**updates)


class DeleteTask(BaseRpcTask):
    name = 'django_rpc.delete'

    def run(self, module_name, class_name, trace):
        model = apps.get_model(module_name, class_name)

        qs = model.objects.get_queryset()
        qs = self.trace_queryset(qs, trace)
        return qs.delete()


class GetOrCreateTask(BaseRpcTask):
    name = 'django_rpc.get_or_create'

    # noinspection PyShadowingNames
    def run(self, module_name, class_name, kwargs, update=False):
        model = apps.get_model(module_name, class_name)
        qs = model.objects.get_queryset()
        if update:
            obj, created = qs.update_or_create(**kwargs)
        else:
            obj, created = qs.get_or_create(**kwargs)

        data = self.serialize(obj, model=model)
        return data, created

if celery.VERSION >= (4, 0, 0):
    fetch = celery_app.register_task(FetchTask())
    insert = celery_app.register_task(InsertTask())
    update = celery_app.register_task(UpdateTask())
    delete = celery_app.register_task(DeleteTask())
    get_or_create = celery_app.register_task(GetOrCreateTask())
else:
    fetch = FetchTask()
    insert = InsertTask()
    update = UpdateTask()
    delete = DeleteTask()
    get_or_create = GetOrCreateTask()
