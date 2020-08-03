import logging
import importlib
from subprocess import check_output
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.models.signals import post_save, post_delete
from infi.django_http_hooks.utils import create_callback
from infi.django_http_hooks.api import create_signal
from .models import Hook

logger = logging.getLogger(__name__)

# stores all current hooks in memory
hooks = {}


def init():
    '''being called only by HooksConfig.ready()'''
    logger.debug('Initialize Django HTTP Hooks')
    all_tables = connection.introspection.table_names()
    if 'hooks_hook' in all_tables:
        post_save.connect(invalidate_hooks, sender=Hook, weak=False)
        post_delete.connect(invalidate_hooks, sender=Hook, weak=False)
        init_hooks()


def invalidate_hooks(**kwargs):
    '''
    Executes a custom command configured in the Django settings of the projects which is using django_http_hooks
    Important: This executed command should reload the server
    '''

    if hasattr(settings, 'DJANGO_HTTP_HOOKS_RELOAD') and settings.DJANGO_HTTP_HOOKS_RELOAD:
        try:
            check_output(settings.DJANGO_HTTP_HOOKS_RELOAD)
        except Exception as e:
            if 'died with <Signals.SIGTERM: 15>' in str(e):
                # if the command failed because of dead process, need to ignore as this is the desired result: restart of the gunicorn server
                pass
            else:
                # logging an error for monitoring purpose
                logger.error('Cannot reload hooks using command {}. Error: {}'.format(settings.DJANGO_HTTP_HOOKS_RELOAD, e))
                # raise exception only if  DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS is set to True
                if hasattr(settings, 'DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS') and settings.DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS:
                    raise
    elif hasattr(settings, 'DJANGO_HTTP_HOOKS_RELOAD_CALLABLE') and settings.DJANGO_HTTP_HOOKS_RELOAD_CALLABLE:
        module_name, callable_name = settings.DJANGO_HTTP_HOOKS_RELOAD_CALLABLE.split(':')
        getattr(importlib.import_module(module_name), callable_name)(**kwargs)
    else:
        logger.warning('Hooks have been changed. Changes wont affect until restarting the server')


def init_hooks(**kwargs):
    '''populate cached variable hooks with all records of Hook model. Should be called for every change in Hook'''
    global hooks
    hooks = {}
    # each key in hooks holds a list of all hooks related to the same model and signal
    try:
        all_hooks = Hook.objects.all()
        # go over all hooks and for each hook go over all its signals
        for h in all_hooks:
            # register only enabled hooks
            if h.enabled:
                for signal in h.signals.all():
                    key_ = '{}_{}'.format(h.model.model, signal.signal)
                    hooks.setdefault(key_, [])
                    # do not register a signal and a model more than once!
                    if not hooks.get(key_):
                        register_signal(signal.signal, h.model)
                    hooks[key_].append(h)
        return hooks
    except Exception as e:
        # raise the exception only if it was configured in the project's settings
        logger.error('Cannot initialize hooks: {}'.format(e))
        if hasattr(settings, 'DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS') and settings.DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS:
            raise


def register_signal(signal_name, model):
    '''create a receiver with dynamic input of signal name
     signal_name is expected to be a comma separated string: <path.to.signal>
    '''
    # create an handler which knows to get signal_name
    handler_ = get_signal_handler_by_name(signal_name)

    # get the signal object in order to connect it to the handler- will raise InvalidSignalHandlerError if signal cannot be imported
    s = create_signal(signal_name, create=False)

    model_cls = apps.get_model(app_label=model.app_label, model_name=model.model)
    s.connect(handler_, weak=False, sender=model_cls)

    logger.debug('registered signal {} with model {}'.format(signal_name, model.name))


def handler(sender, signal_, **kwargs):
    '''being triggered by registered signals and create a callback according to the hook found in cached hooks'''
    try:
        global hooks
        # search for the hook of the given sender and signal name according to key composed from signal_name & sender
        hook_key = '{}_{}'.format(sender.__name__.lower(), signal_)

        hooks_list = hooks.get(hook_key, [])
        for hook in hooks_list:
            # differentiate between post_save/pre_save caused by create event against update event
            if 'save' in signal_:
                event_type = 'created' if kwargs.get('created') else 'updated'
            else:
                # if the signal is not post_save/pre_save the event type will be just the signal
                event_type = signal_

            create_callback(hook, event_type=event_type, **kwargs)
    except Exception as e:
        logger.error('Error in Signal handler: {}'.format(e))
        # raise the exception only if it was configured in the project's settings
        if hasattr(settings, 'DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS') and settings.DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS:
            raise


def get_signal_handler_by_name(signal_name):
    '''wrapper for handler, sending it the signal name, to be use in handler'''
    def signal_handler(sender, **kwargs):
        handler(sender, signal_name, **kwargs)
    return signal_handler

