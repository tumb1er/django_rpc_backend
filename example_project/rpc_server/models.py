from django.db import models


class ServerModel(models.Model):
    char_field = models.CharField(max_length=32, blank=True, null=True)
    int_field = models.IntegerField()
