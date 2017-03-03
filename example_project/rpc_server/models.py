from django.db import models
from django.utils.timezone import now


class ServerModel(models.Model):
    char_field = models.CharField(max_length=32, blank=True, null=True)
    dt_field = models.DateTimeField(default=now)
