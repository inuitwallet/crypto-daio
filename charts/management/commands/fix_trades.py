import logging
from django.core.management import BaseCommand

from charts.models import Trade

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        for trade in Trade.objects.all():
            if trade.total is None:
                if trade.amount is None:
                    logger.error('{} amount is None'.format(trade))
                    continue

                if trade.rate is None:
                    logger.error('{} rate is None'.format(trade))
                    continue

                trade.total = trade.amount * trade.rate
                trade.save()
                logger.info('set total on {}'.format(trade))
