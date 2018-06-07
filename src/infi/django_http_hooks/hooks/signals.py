import logging
from subprocess import check_output
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.models.signals import post_save, post_delete
from infi.django_http_hooks.utils import create_callback
from infi.django_http_hooks.api import create_signal
from models import Hook

logger = logging.getLogger(__name__)

# stores all current hooks in memory
hooks = {}


def init():
    logger.info('Initialize Django HTTP Hooks')
    all_tables = connection.introspection.table_names()
    if 'hooks_hook' in all_tables:
        post_save.connect(invalidate_hooks, sender=Hook, weak=False)
        post_delete.connect(invalidate_hooks, sender=Hook, weak=False)
        init_hooks()


def invalidate_hooks(**kwargs):
    # executes a custom command configured in the Django settings of the projects which is using django_http_hooks
    # this command should reload the server
    if hasattr(settings, 'DJANGO_HTTP_HOOKS_RELOAD') and settings.DJANGO_HTTP_HOOKS_RELOAD:
        try:
            check_output(settings.DJANGO_HTTP_HOOKS_RELOAD)
        except Exception:
            logger.error('Cannot reload hooks')
            if hasattr(settings, 'DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS') and settings.DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS:
                raise
    else:
        logger.warning('Hooks have been changed. Changes wont affect until restarting the server')


def init_hooks(**kwargs):
    '''should be called for every change in Hook model'''
    global hooks
    try:
        all_hooks = Hook.objects.all()
        # go over all hooks and for each hook go over all its signals
        # Can be only one appearance of each Model in all_hooks
        for h in all_hooks:
            for signal in h.signals.all():
                # if the same hook (model & signal) is already registered, do not register the signal again. Only updating hooks
                if not hooks.get('{}_{}'.format(h.model, signal.signal)):
                    register_signal(signal.signal, h.model)
                hooks['{}_{}'.format(h.model, signal.signal)] = h
    except Exception, e:
        # raise the exception only if it was configured in the project's settings
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

    model_cls = apps.get_model(app_label=model.app_label, model_name=model.name)
    s.connect(handler_, weak=False, sender=model_cls)

    logger.info('registered signal {} with model {}'.format(signal_name, model.name))


def handler(sender, signal_, **kwargs):
    '''being triggered by registered signals and create a callback according to the hook'''
    try:
        global hooks
        hook_key = '{}_{}'.format(sender.__name__.lower(), signal_)

        hook = hooks.get(hook_key)
        if hook:
            # differentiate between post_save/pre_save caused by create event against update event
            if 'save' in signal_:
                event_type = 'created' if kwargs.get('created') else 'updated'
            else:
                # if the signal is not post_save/pre_save the event type will be just the signal
                event_type = signal_

            create_callback(hook, event_type=event_type, **kwargs)
    except Exception, e:
        logger.error('Error in Signal handler: {}'.format(e))
        # raise the exception only if it was configured in the project's settings
        if hasattr(settings, 'DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS') and settings.DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS:
            raise


def get_signal_handler_by_name(signal_name):
    def signal_handler(sender, **kwargs):
        handler(sender, signal_name, **kwargs)
    return signal_handler

