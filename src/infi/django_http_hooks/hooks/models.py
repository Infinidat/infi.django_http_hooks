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

    # Signal details: An hook can be connected to multiple signals.
    model               = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    signals             = models.ManyToManyField(Signal)
    enabled             = models.BooleanField(default=True)

    # Hook HTTP Request details.
    target_url          = models.URLField(max_length=512)
    http_method         = models.CharField(max_length=64, default='POST', choices=[(m, m) for m in HTTP_METHODS])
    headers             = models.TextField(null=True, blank=True, help_text='Headers should be pairs of key & value seperated by ":" and each pair should be in a new row. E.g: api-key: 12345 ')
    payload_template    = models.TextField(null=True, blank=True, help_text='Use {{}} for variables template. Placeholder names can be any attribute in the model using a prefix of "instance.". Leave empty for default payload. See documentation for further details.  ')
    serializer_class    = models.CharField(max_length=256, null=True, blank=True, help_text='Full path of the serializer class. Leave empty for default payload.')
    content_type        = models.CharField(max_length=128, null=True, blank=True, choices=[(c, c) for c in CONTENT_TYPES])


    def __str__(self):
        return '{name}({date})'.format(name=self.name or self.model.name, date=self.create_datetime.date())


class Callback(models.Model):
    update_datetime     = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    create_datetime     = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    target_url          = models.URLField(max_length=512)
    headers             = models.TextField(null=True, blank=True)
    payload             = models.TextField(null=True, blank=True)
    content_type        = models.CharField(max_length=128, null=True, blank=True)
    http_method         = models.CharField(max_length=64, null=True, blank=True, choices=[(m, m) for m in HTTP_METHODS])

    hook                = models.ForeignKey(Hook, on_delete=models.CASCADE)

    status              = models.CharField(max_length=64, null=True, blank=True, choices=[('waiting', 'waiting'), ('sent', 'sent'), ('error', 'error')], default='waiting')
    # storing the error details - after trying to send the request
    status_details      = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return '{}_{}'.format(self.update_datetime, self.hook)






