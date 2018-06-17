from django.utils import timezone
from django.template import Template, Context
from django.core import serializers
from infi.django_http_hooks.hooks.models import Callback
from .exceptions import *
import json
from importlib import import_module
import logging

logger = logging.getLogger(__name__)


def create_callback(hook, **kwargs):
    '''
    Create a new callback to be sent by background process
    :param hook: Hook object
    :param kwargs: Contains instance and other inputs came from the signal
    :return:
    '''
    now_ = timezone.now()
    try:
        callback = Callback(update_datetime = now_,
                            create_datetime = now_,
                            target_url      = hook.target_url,
                            http_method     = hook.http_method,
                            hook            = hook)

        callback.payload = set_payload(hook, **kwargs)
        callback.headers = validate_headers(hook.headers) if hook.headers else hook.headers
    except (InvalidPayloadError, InvalidHeadersError), e:
        # if there are invalid payload or invalid headers, mark the callback with error
        callback.status = 'error'
        callback.status_details = e.message

    callback.save()

    return callback


def validate_headers(headers):
    try:
        json.loads(headers)
        return headers
    except ValueError:
        raise InvalidHeadersError('invalid headers: {}'.format(headers))


def set_payload(hook, **kwargs):

    instance = kwargs.get('instance')
    # setting payload
    if hook.payload_template:
        context = dict()
        context.update(kwargs)
        context.update(instance.__dict__)
        template = Template(hook.payload_template)
        c = Context(context)
        payload = template.render(c)
        try:
            json.loads(payload)
        except ValueError:
            logger.error('Payload template created an invalid JSON: {}'.format(payload))
            raise InvalidPayloadError('Payload template created an invalid JSON: {}'.format(payload))

    elif hook.serializer_class:
        # serializer_class is expected to be a comma separated string: <path.to.serializer_class>
        serializer = dynamic_import(hook.serializer_class)
        if not serializer:
            logger.error('cannot import serializer class {}'.format(hook.serializer_class))
            raise InvalidPayloadError('cannot import serializer class {}'.format(hook.serializer_class))
        try:
            # executes to_representation of the given serializer and dump it to json
            payload = json.dumps(serializer().to_representation(instance))
        except Exception, e:
            logger.error('cannot execute to_representation with the given serializer: {}'.format(e.message))
            raise InvalidPayloadError('cannot execute to_representation with the given serializer: {}'.format(e.message))
    else:
        # default payload
        # convert the json list to dict: trim the '[' and ']' and load the json dict
        object_serialization = json.loads(serializers.serialize('json', [instance])[1:-1])
        payload = json.dumps({
            # object_serialization['model'] contains the full path of the model
            'object_type': object_serialization.get('model'),
            'object_id': object_serialization.get('pk'),
            'event_type': kwargs.get('event_type'),
            'object_serialization': object_serialization.get('fields')
        })

    return payload


def dynamic_import(package_path):
    try:
        path_list = package_path.split('.')
        module = import_module('.'.join(path_list[:-1]))
        res = getattr(module, path_list[-1])
        return res
    except Exception:
        return None