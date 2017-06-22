import csv
import datetime
from decimal import Decimal
import logging

import requests
from django.core.management import BaseCommand
from django.db import IntegrityError
from django.utils.timezone import make_aware
from charts.models import Trade, Pair, CurrencyValue, Currency

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    @staticmethod
    def do_cryptopia():
        with open('charts/old_orders/cryptopia.csv') as cryptopia_csv:
            csv_reader = csv.reader(cryptopia_csv)

            for row in csv_reader:
                if row[0] == '#':
                    continue
                text_pair = row[1]
                currencies = text_pair.split('/')
                quote = currencies[0]
                base = currencies[1]

                try:
                    pair = Pair.objects.get(
                        quote_currency__code=quote,
                        base_currency__code=base
                    )
                except Pair.DoesNotExist:
                    continue

                trade, _ = Trade.objects.get_or_create(
                    order_id=row[0],
                    pair=pair
                )
                trade.order_type = 'SELL' if row[2] == 'Sell' else 'BUY'
                trade.rate = Decimal(row[3])
                trade.amount = Decimal(row[4])
                trade.total = Decimal(row[5])
                trade.date_time = make_aware(
                    datetime.datetime.strptime(row[6], '%d/%m/%Y %I:%M:%S %p')
                )

                trade.save()
                logger.info('Saved Trade {}'.format(trade))

    @staticmethod
    def do_bittrex():
        with open('charts/old_orders/bittrex.csv') as bittrex_csv:
            csv_reader = csv.reader(bittrex_csv)

            for row in csv_reader:
                if row[0] == 'OrderUuid':
                    continue
                text_pair = row[1]
                currencies = text_pair.split('-')
                quote = currencies[1]
                base = currencies[0]

                try:
                    pair = Pair.objects.get(
                        quote_currency__code=quote,
                        base_currency__code=base
                    )
                except Pair.DoesNotExist:
                    continue

                trade, _ = Trade.objects.get_or_create(
                    order_id=row[0],
                    pair=pair
                )
                trade.order_type = 'SELL' if row[2] == 'LIMIT_SELL' else 'BUY'
                trade.amount = Decimal(row[3])
                trade.rate = Decimal(row[6])
                trade.fee = Decimal(row[5])
                trade.date_time = make_aware(
                    datetime.datetime.strptime(row[8], '%m/%d/%Y %I:%M:%S %p')
                )
                trade.save()
                trade.total = trade.amount * trade.rate
                trade.save()
                logger.info('Saved Trade {}'.format(trade))

    @staticmethod
    def get_2017_bitcoin_prices():
        bitcoin_currency = Currency.objects.get(code='BTC')
        # get BTC prices from CoinDesk
        earliest_current = CurrencyValue.objects.filter(
            currency__code='BTC'
        ).order_by(
            'date_time'
        ).values_list(
            'date_time', flat=True
        ).first().isoformat().split('T')[0]
        r = requests.get(
            url='http://api.coindesk.com/v1/bpi/historical/close.json?'
                'start={}&end={}'.format(
                    datetime.datetime(2017, 1, 1, 0, 0, 0).isoformat().split('T')[0],
                    earliest_current
                )
        )

        try:
            coindesk = r.json()
        except ValueError:
            print(r.text)
            return

        bitcoin_prices = coindesk['bpi']

        for date in bitcoin_prices:
            date_parts = date.split('-')
            date_time = make_aware(
                datetime.datetime(
                    int(date_parts[0]),
                    int(date_parts[1]),
                    int(date_parts[2]),
                    0,
                    0,
                    0
                )
            )
            try:
                currency_value = CurrencyValue.objects.create(
                    currency=bitcoin_currency,
                    date_time=date_time,
                    usd_value=bitcoin_prices[date]
                )
            except IntegrityError:
                continue
            logger.info('saved {}'.format(currency_value))

    def handle(self, *args, **options):
        #self.do_cryptopia()
        #self.do_bittrex()
        self.get_2017_bitcoin_prices()
