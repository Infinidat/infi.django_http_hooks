# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from models import Hook, Callback, Signal


class HookAdmin(admin.ModelAdmin):
    list_display = ('name', 'model', 'target_url', 'create_datetime', 'update_datetime')
    search_fields = ('model', 'name', 'target_url')
    filter_horizontal = ('signals',)


class CallbackAdmin(admin.ModelAdmin):
    list_display = ('hook', 'status', 'status_details', 'create_datetime')
    search_fields = ('hook', 'name')


class SignalAdmin(admin.ModelAdmin):
    list_display = ('signal', 'create_datetime')
    search_fields = ('signal', )




admin.site.register(Hook, HookAdmin)
admin.site.register(Callback, CallbackAdmin)
admin.site.register(Signal, SignalAdmin)