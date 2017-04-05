from django.db import models
from django.utils.timezone import now

from django_rpc.models import DjangoRpcModel


class FKClientModel(DjangoRpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'FKModel'

    name = models.CharField(max_length=5, blank=True)


class ClientModel(DjangoRpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'ServerModel'

    char_field = models.CharField(max_length=32, blank=True)
    int_field = models.IntegerField()
    dt_field = models.DateTimeField(default=now)
    fk = models.ForeignKey('FKClientModel', null=True, blank=True,
                           related_name='servermodel')
