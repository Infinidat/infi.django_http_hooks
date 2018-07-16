from logging import getLogger
from django.utils import timezone
from django.core.management.base import BaseCommand
from infi.django_http_hooks.hooks.models import Callback
from datetime import timedelta
import sys
logger = getLogger(__name__)

class Command(BaseCommand):

    help = 'Monitor callbacks according to given time range and limits'

    def add_arguments(self, parser):
        parser.add_argument('--minutes_ago', type=int, help='check if there are more than the given amount of waiting callbacks')
        parser.add_argument('--callbacks_limit', type=int, help='limit for callbacks in the last minutes ago', default=10)
        parser.add_argument('--status', type=str, help='Callback type to check: waiting/error', required=True)


    def handle(self, *args, **options):
        filter_ = dict(status=options['status'])
        since_when = None
        if options.get('minutes_ago'):
            now_ = timezone.now()
            since_when = now_ - timedelta(minutes=options['minutes_ago'])

            filter_["update_datetime__gt"] = since_when

            logger.info('Checks for {} callbacks since {}'.format(options['status'], since_when.strftime('%Y-%m-%d %H:%M:%S')))

        callbacks = Callback.objects.filter(**filter_)
        callbacks_amt = len(callbacks)
        if callbacks_amt >= options['callbacks_limit']:
            logger.warn('There are {} {} callbacks in the queue since {}'.format(callbacks_amt, options['status'], since_when.strftime('%Y-%m-%d %H:%M:%S') if since_when else 'beginning of time.'))
            sys.exit(1)
