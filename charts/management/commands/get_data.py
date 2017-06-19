import logging
from django.core.management import BaseCommand
from django.db import connection
import charts.wrappers as wrappers
from charts.models import Currency

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):

        # get balance and trade data
        chain = connection.tenant
        for exchange in chain.exchanges.all():
            exchange_wrappper = getattr(wrappers, exchange.name)
            wrapper = exchange_wrappper(
                api_key=exchange.api_key,
                api_secret=exchange.api_secret,
                base_url=exchange.api_base
            )
            for pair in exchange.pairs.all():
                logger.info('getting trade history for {}'.format(pair))
                wrapper.get_trade_history(pair)
                logger.info('getting balance for {}'.format(pair))
                wrapper.get_balances(pair)

        # get the usd values of currencies that need it
        logger.info('fetching usd values for currencies')
        cmc = wrappers.CoinMarketCap()
        cmc.get_usd_values(
            Currency.objects.filter(get_usd_value=True)
        )

