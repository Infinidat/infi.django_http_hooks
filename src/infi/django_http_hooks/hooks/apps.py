# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from django.apps import AppConfig
from django.conf import settings

class HooksConfig(AppConfig):
    name = 'infi.django_http_hooks.hooks'

    def ready(self):
        # Do not initialize hooks if settings.DJANGO_HTTP_HOOKS_SHUT_DOWN == True
        if not (hasattr(settings, 'DJANGO_HTTP_HOOKS_SHUT_DOWN') and settings.DJANGO_HTTP_HOOKS_SHUT_DOWN):
            from . import signals
            # do not run init in test mode- in test mode each change in Hook triggers manually the function init_hooks
            if not ('test' in sys.argv):
                signals.init()




