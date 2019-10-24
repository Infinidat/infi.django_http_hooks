# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings

COMMON_SIGNALS = ['django.db.models.signals.post_save',
                  'django.db.models.signals.pre_save',
                  'django.db.models.signals.post_delete',
                  'django.db.models.signals.pre_init',
                  'django.db.models.signals.post_init',
                  'django.db.models.signals.pre_delete']



def create_signals(apps, schema_editor):
    signal_model = apps.get_model("hooks", "Signal")
    for signal in COMMON_SIGNALS:
        signal_model.objects.create(signal=signal)


def delete_signals(apps, schema_editor):
    signal_model = apps.get_model("hooks", "Signal")
    signal_model.objects.filter(signal__in=COMMON_SIGNALS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('hooks', '0001_initial')
    ]

    operations = [
        migrations.RunPython(create_signals, reverse_code=delete_signals)
    ]
