from django.db import models

from django_rpc.models import DjangoRpcModel


class ClientModel(DjangoRpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'ServerModel'

    char_field = models.CharField(max_length=32)
    dt_field = models.DateTimeField()


ClientModel.objects.get_queryset()