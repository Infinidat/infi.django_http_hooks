# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-06-06 11:51
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Callback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('update_datetime', models.DateTimeField(blank=True, null=True)),
                ('create_datetime', models.DateTimeField(blank=True, null=True)),
                ('target_url', models.CharField(max_length=256)),
                ('headers', models.CharField(blank=True, max_length=2048, null=True)),
                ('payload', models.CharField(blank=True, max_length=4096, null=True)),
                ('content_type', models.CharField(blank=True, max_length=128, null=True)),
                ('http_method', models.CharField(blank=True, max_length=64, null=True)),
                ('status', models.CharField(blank=True, choices=[('waiting', 'waiting'), ('sent', 'sent'), ('error', 'error')], default='waiting', max_length=64, null=True)),
                ('status_details', models.CharField(blank=True, max_length=512, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Hook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('update_datetime', models.DateTimeField(blank=True, null=True)),
                ('create_datetime', models.DateTimeField(blank=True, null=True)),
                ('target_url', models.CharField(max_length=256)),
                ('headers', models.CharField(blank=True, max_length=2048, null=True)),
                ('payload_template', models.CharField(blank=True, max_length=2048, null=True)),
                ('serializer_class', models.CharField(blank=True, help_text='Full path of the serializer class', max_length=256, null=True)),
                ('content_type', models.CharField(blank=True, max_length=128, null=True)),
                ('http_method', models.CharField(blank=True, max_length=64, null=True)),
                ('comments', models.CharField(blank=True, max_length=1024, null=True)),
                ('model', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='Signal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signal', models.CharField(help_text='Full path of the signal class', max_length=256, unique=True)),
                ('update_time', models.DateTimeField(blank=True, null=True)),
                ('create_datetime', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='hook',
            name='signals',
            field=models.ManyToManyField(to='hooks.Signal'),
        ),
        migrations.AddField(
            model_name='hook',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='callback',
            name='hook',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hooks.Hook'),
        ),
    ]
