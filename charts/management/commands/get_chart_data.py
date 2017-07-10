import logging
from django.core.management import BaseCommand
from django.db import connection
import charts.wrappers as wrappers
import charts.wrappers.address_wrappers as address_wrappers
from charts.models import Currency, WatchedAddress

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

                logger.info('getting open orders for {}'.format(pair))
                wrapper.get_open_orders(pair)

                logger.info('getting withdrawals for {}'.format(pair))
                wrapper.get_withdrawals(pair)

                logger.info('getting deposits for {}'.format(pair))
                wrapper.get_deposits(pair)

        # get watched address data
        logger.info('fetching balances for watched addresses')
        for watched_address in WatchedAddress.objects.all():
            address_wrapper = getattr(address_wrappers, watched_address.currency.code)
            wrapper = address_wrapper()
            wrapper.get_address_balance(watched_address)

        # get the usd values of currencies that need it
        logger.info('fetching usd values for currencies')
        cmc = wrappers.CoinMarketCap()
        cmc.get_usd_values(
            Currency.objects.filter(get_usd_value=True)
        )

