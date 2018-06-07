# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth.models import User


class Signal(models.Model):
    signal              = models.CharField(max_length=256, unique=True, help_text='Full path of the signal class')
    update_time         = models.DateTimeField(null=True, blank=True)
    create_datetime     = models.DateTimeField(null=True, blank=True)
    user                = models.ForeignKey(User)

    def __str__(self):
        return self.signal


class Hook(models.Model):
    update_datetime     = models.DateTimeField(null=True, blank=True)
    create_datetime     = models.DateTimeField(null=True, blank=True)
    # Signal details: Can be only one Hook for a model. An hook can be connected to multiple signals.
    model               = models.OneToOneField(ContentType, blank=True, null=True)
    signals             = models.ManyToManyField(Signal)

    # Hook HTTP Request details.
    target_url          = models.CharField(max_length=256)
    http_method         = models.CharField(max_length=64, null=True, blank=True)
    headers             = models.CharField(max_length=2048, null=True, blank=True)
    payload_template    = models.CharField(max_length=2048, null=True, blank=True)
    serializer_class    = models.CharField(max_length=256,null=True, blank=True, help_text='Full path of the serializer class')
    content_type        = models.CharField(max_length=128, null=True, blank=True)

    # for internal use, visible in admin only
    comments            = models.CharField(max_length=1024, null=True, blank=True)
    user                = models.ForeignKey(User)

    def __str__(self):
        return '{}_###({})###'.format(self.model, ','.join([s.signal for s in self.signals.all()]))


class Callback(models.Model):
    update_datetime     = models.DateTimeField(null=True, blank=True)
    create_datetime     = models.DateTimeField(null=True, blank=True)

    target_url          = models.CharField(max_length=256)
    headers             = models.CharField(max_length=2048, null=True, blank=True)
    payload             = models.CharField(max_length=4096, null=True, blank=True)
    content_type        = models.CharField(max_length=128, null=True, blank=True)
    http_method         = models.CharField(max_length=64, null=True, blank=True)

    hook                = models.ForeignKey(Hook)

    status              = models.CharField(max_length=64, null=True, blank=True, choices=[('waiting', 'waiting'), ('sent', 'sent'), ('error', 'error')], default='waiting')
    # storing the error details - after trying to send the request
    status_details      = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return '{}_{}'.format(self.update_datetime, self.hook)






