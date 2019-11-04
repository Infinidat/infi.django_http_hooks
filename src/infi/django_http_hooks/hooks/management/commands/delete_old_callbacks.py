from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from logging import getLogger
from datetime import timedelta
from infi.django_http_hooks.hooks.models import Callback


logger = getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete old callbacks. Keep only callbacks created later than the given number of days back'


    def add_arguments(self, parser):
        parser.add_argument('days_back', type=int)

    def handle(self, *args, **options):
        now_ = timezone.now()
        date_to_delete_from = now_ - timedelta(days=options['days_back'])
        table_name = Callback._meta.db_table
        callbacks_to_delete = Callback.objects.filter(create_datetime__lt=date_to_delete_from)
        if callbacks_to_delete:
            logger.info('About to delete {} callbacks before {}'.format(callbacks_to_delete.count(), date_to_delete_from))
            callbacks_to_delete.delete()

            cursor = connection.cursor()
            cursor.execute('VACUUM ANALYZE {}'.format(table_name))

            logger.info('Executed VACUUM ANALYZE on table {}'.format(table_name))
        else:
            logger.info('No callbacks were deleted')