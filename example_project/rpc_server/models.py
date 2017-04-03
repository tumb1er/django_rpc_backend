from django.db import models
from django.utils.timezone import now


class FKModel(models.Model):
    name = models.CharField(max_length=5, blank=True, null=True)


class ServerModel(models.Model):
    char_field = models.CharField(max_length=32, blank=True, null=True)
    int_field = models.IntegerField()
    dt_field = models.DateTimeField(default=now)

    fk = models.ForeignKey('FKModel', null=True, blank=True)
