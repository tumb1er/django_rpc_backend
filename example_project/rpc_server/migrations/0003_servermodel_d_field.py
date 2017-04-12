# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('rpc_server', '0002_auto_20170403_0617'),
    ]

    operations = [
        migrations.AddField(
            model_name='servermodel',
            name='d_field',
            field=models.DateField(default=datetime.date.today),
        ),
    ]
