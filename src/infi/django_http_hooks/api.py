import sys
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from infi.django_http_hooks.hooks.models import Hook, Signal

from infi.django_http_hooks.utils import dynamic_import

from .exceptions import *


def create_signal(signal, create=True, **kwargs):
    '''
    validate that the given signal can be imported. If not, raise InvalidSignalError
    :param signal: Full path of the signal
    :param create: A flag to indicate if need to create the signal object. If False, returns the Signal object
    :param kwargs: Additional inputs for the Signal object
    :return: A Signal object if created, otherwise returns the object of the given Signal path
    '''

    s = dynamic_import(signal)
    if not s:
        raise InvalidSignalError()

    if create:
        now_ = timezone.now()
        signal_, created = Signal.objects.get_or_create(signal=signal,
                                                        defaults={'user': kwargs.get('user'),
                                                                  'update_time': now_,
                                                                  'create_datetime': now_})
        return signal_
    else:
        return s


def create_hook(signals, model=None, **kwargs):
    '''creating an hook with the given model and signal. Being called by any test which requires an hook'''
    from infi.django_http_hooks.hooks.signals import init_hooks

    hook = Hook(model            =ContentType.objects.get(model=model),
                target_url       =kwargs.get('target_url', 'demo url'),
                http_method      =kwargs.get('http_method'),
                user             =kwargs.get('user'),
                headers          =kwargs.get('headers'),
                payload_template =kwargs.get('payload_template'),
                serializer_class =kwargs.get('serializer_class'),
                content_type     =kwargs.get('content_type'))
    hook.save()
    for signal in signals:
        signal_ = create_signal(signal, create=True, user=kwargs.get('user'))

        hook.signals.add(signal_)

    # calling init_hooks to register all signals only in testing mode. Not in testing, the init_hooks will be triggered automatically by invalidate_hooks
    if 'test' in sys.argv:
        init_hooks()
    return hook