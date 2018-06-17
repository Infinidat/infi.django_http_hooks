# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from models import Hook, Callback, Signal

admin.site.register(Hook)
admin.site.register(Callback)
admin.site.register(Signal)