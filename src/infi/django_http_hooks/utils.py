from django.utils import timezone
from django.template import Template, Context
from django.core import serializers
from infi.django_http_hooks.hooks.models import Callback
from .exceptions import *
from importlib import import_module
import logging
import json

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
                            content_type    = hook.content_type,
                            hook            = hook)

        callback.payload = set_payload(hook, **kwargs)
        callback.headers = validate_headers(hook.headers) if hook.headers else hook.headers
    except (InvalidPayloadError, InvalidHeadersError) as e:
        # if there are invalid payload or invalid headers, mark the callback with error
        callback.status = 'error'
        callback.status_details = str(e)

    callback.save()

    return callback


def validate_headers(headers):
    '''
    Expected headers is pair of values (key:value) separated by a new line e.g:

    headers_key_1: headers_value_1
    headers_key_2: headers_value_2
    ...

    '''
    try:
        headers_dict = {row.split(':')[0].strip(): row.split(':')[1].strip() for row in headers.split('\r\n')}
        headers_json = json.dumps(headers_dict)
        return headers_json
    except (ValueError, IndexError):
        raise InvalidHeadersError('invalid headers: {}'.format(headers))


def validate_payload(payload, content_type):
    ''' Validate that the given payload is valid against the given content-type. If not given content the validation passes'''
    if content_type == 'application/json':
        try:
            json.loads(payload)
        except ValueError:
            logger.error('Payload is an invalid JSON: {}'.format(payload))
            raise InvalidPayloadError('Payload is an invalid JSON: {}'.format(payload))
    elif content_type in ['application/xml', 'text/xml']:
        from lxml import etree
        xml = bytes(bytearray(payload, encoding="utf-8"))
        try:
            etree.XML(xml)
        except etree.XMLSyntaxError:
            logger.error('Payload is an invalid xml: {}'.format(payload))
            raise InvalidPayloadError('Payload is an invalid XML: {}'.format(payload))


def set_payload(hook, **kwargs):
    '''Set the payload according to given payload_tamplate or serializer_class. If both are missing returns a default payload'''
    instance = kwargs.get('instance')
    # setting payload
    if hook.payload_template:
        context = dict(instance=instance)
        context.update(kwargs)
        c = Context(context)
        template = Template(hook.payload_template)
        payload = template.render(c)

    elif hook.serializer_class:
        # serializer_class is expected to be a comma separated string: <path.to.serializer_class>
        serializer = dynamic_import(hook.serializer_class)
        if not serializer:
            logger.error('cannot import serializer class {}'.format(hook.serializer_class))
            raise InvalidPayloadError('cannot import serializer class {}'.format(hook.serializer_class))
        try:
            # executes to_representation of the given serializer and dump it to json
            payload = json.dumps(serializer().to_representation(instance))
        except Exception as e:
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

    validate_payload(payload, hook.content_type)
    return payload


def dynamic_import(package_path):
    try:
        path_list = package_path.split('.')
        module = import_module('.'.join(path_list[:-1]))
        res = getattr(module, path_list[-1])
        return res
    except Exception:
        return None