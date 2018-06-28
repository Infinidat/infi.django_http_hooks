# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.contenttypes.models import ContentType
from django.db import models



HTTP_METHODS = ['POST', 'PUT', 'PATCH', 'GET', 'DELETE']

CONTENT_TYPES = ['application/json', 'application/xml', 'text/xml', 'text/plain','application/javascript', 'text/html']

class Signal(models.Model):
    signal              = models.CharField(max_length=256, unique=True, help_text='Full path of the signal class')
    update_time         = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    create_datetime     = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    def __str__(self):
        return self.signal


class Hook(models.Model):
    name = models.CharField(max_length=512, null=True, blank=True)
    update_datetime     = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    create_datetime     = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    # Signal details: Can be only one Hook for a model. An hook can be connected to multiple signals.
    model               = models.OneToOneField(ContentType, blank=True, null=True)
    signals             = models.ManyToManyField(Signal)

    # Hook HTTP Request details.
    target_url          = models.URLField(max_length=512)
    http_method         = models.CharField(max_length=64, null=True, blank=True, choices=[(m, m) for m in HTTP_METHODS])
    headers             = models.TextField(null=True, blank=True)
    payload_template    = models.TextField(null=True, blank=True, help_text='Use {{}} for any variable template')
    serializer_class    = models.CharField(max_length=256, null=True, blank=True, help_text='Full path of the serializer class')
    content_type        = models.CharField(max_length=128, null=True, blank=True, choices=[(c, c) for c in CONTENT_TYPES])



    def __str__(self):
        return '{name}({date})'.format(name=self.name, date=self.create_datetime.date())


class Callback(models.Model):
    update_datetime     = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    create_datetime     = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    target_url          = models.URLField(max_length=512)
    headers             = models.TextField(null=True, blank=True)
    payload             = models.TextField(null=True, blank=True)
    content_type        = models.CharField(max_length=128, null=True, blank=True)
    http_method         = models.CharField(max_length=64, null=True, blank=True, choices=[(m, m) for m in HTTP_METHODS])

    hook                = models.ForeignKey(Hook)

    status              = models.CharField(max_length=64, null=True, blank=True, choices=[('waiting', 'waiting'), ('sent', 'sent'), ('error', 'error')], default='waiting')
    # storing the error details - after trying to send the request
    status_details      = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return '{}_{}'.format(self.update_datetime, self.hook)






