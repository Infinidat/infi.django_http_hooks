# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from .models import Hook, Callback, Signal


class HookAdmin(admin.ModelAdmin):
    list_display = ('name', 'model', 'target_url', 'create_datetime', 'update_datetime', 'enabled')
    search_fields = ('model', 'name', 'target_url')
    filter_horizontal = ('signals',)

    fieldsets = (
        ('General Hook Details', {
            'fields': ('name', 'enabled', 'model', 'signals')
        }),
        ('Hook HTTP Request Details', {
            'fields': ('target_url', 'http_method', 'headers', 'content_type', 'payload_template', 'serializer_class')
        }),
    )


class CallbackAdmin(admin.ModelAdmin):
    list_display = ('hook', 'status', 'status_details', 'create_datetime')
    search_fields = ('hook', 'target_url', 'status_details')
    list_filter = [('hook', RelatedDropdownFilter), 'status']

class SignalAdmin(admin.ModelAdmin):
    list_display = ('signal', 'create_datetime')
    search_fields = ('signal', )




admin.site.register(Hook, HookAdmin)
admin.site.register(Callback, CallbackAdmin)
admin.site.register(Signal, SignalAdmin)