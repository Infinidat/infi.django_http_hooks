from logging import getLogger
from django.utils import timezone
from django.core.management.base import BaseCommand
from infi.django_http_hooks.hooks.models import Callback
from infi.django_http_hooks.http_requests import send_request
from requests.exceptions import HTTPError, ConnectionError

logger = getLogger(__name__)

class Command(BaseCommand):

    help = 'Send HTTP request for any waiting callback'

    def add_arguments(self, parser):
        parser.add_argument('--hook_id', type=str, help='Send only requests related to given hook')
        parser.add_argument('--callbacks', nargs='*', type=str, help='List of callbacks to send')

    def handle(self, *args, **options):
        filter_ = {'status': 'waiting'}
        if options['hook_id']:
            filter_['hook_id'] = options['hook_id']
        elif options['callbacks']:
            filter_['id__in'] = options['callbacks']

        callbacks_to_send = Callback.objects.filter(**filter_)

        run_time = timezone.now()
        errors = 0
        if callbacks_to_send:
            for idx, callback in enumerate(callbacks_to_send):
                res = None
                try:
                    res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)
                    callback.status = 'sent'
                    callback.status_details = u'status_code:{status_code}'.format(status_code=res.status_code)
                except (HTTPError, ConnectionError) as e:
                    callback.status_details = u'status_code:{status_code}-{error_msg}'.format(status_code=res.status_code if res else '#N/A', error_msg=e)
                    callback.status = 'error'
                    errors += 1
                callback.update_datetime = run_time
                callback.save()

            logger.info('Sent {} requests. {} requests failed.'.format(idx + 1, errors))
