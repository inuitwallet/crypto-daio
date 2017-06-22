import datetime
import time

from decimal import Decimal
from django.db import connection
from django.db.models import Min, Max, Avg
from django.shortcuts import render
from django.utils.timezone import make_aware
from django.views import View
from django.views.generic import ListView

from blocks.models import Info
from charts.models import Balance, Trade, CurrencyValue


class TradeValueTable(ListView):
    model = Trade
    ordering = '-date_time'
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super(TradeValueTable, self).get_context_data(**kwargs)
        new_object_list = []
        for trade in context['object_list']:
            if not trade.date_time:
                continue

            trade.adjusted_amount = trade.amount
            if trade.pair.quote_currency.get_usd_value:
                closest_value = CurrencyValue.objects.get_closest_to(
                    trade.pair.quote_currency,
                    trade.date_time
                ).usd_value
                trade.quote_price = closest_value
                if trade.amount and closest_value:
                    trade.adjusted_amount = trade.amount * closest_value

            trade.adjusted_rate = trade.rate
            trade.adjusted_total = trade.total
            if trade.pair.base_currency.get_usd_value:
                closest_value = CurrencyValue.objects.get_closest_to(
                    trade.pair.base_currency,
                    trade.date_time
                ).usd_value
                trade.base_price = closest_value
                if trade.rate and closest_value:
                    trade.adjusted_rate = trade.rate * closest_value
                if trade.total and closest_value:
                    trade.adjusted_total = trade.total * closest_value

            new_object_list.append(trade)

        context['object_list'] = new_object_list
        context['chain'] = connection.schema_name
        return context




class NAVChart(View):
    @staticmethod
    def get(request):
        x_data = []
        y_data = {}
        low_date = Balance.objects.all().aggregate(
            Min('date_time')
        )
        low_date = low_date['date_time__min']
        max_date = Balance.objects.all().aggregate(
            Max('date_time')
        )
        max_date = max_date['date_time__max']

        exchanges = list(connection.tenant.exchanges.all())

        currency_totals = {}

        for exchange in exchanges:
            y_data[exchange.name] = {}
            currency_totals[exchange] = {}
            for currency in exchange.currencies.all():
                currency_totals[exchange][currency] = Decimal(0)

        while low_date < max_date:
            midnight = make_aware(
                datetime.datetime(
                    low_date.year,
                    low_date.month,
                    low_date.day,
                    0,
                    0,
                    0
                )
            )
            tomorrow = midnight + datetime.timedelta(days=1)
            day = int(time.mktime(tomorrow.timetuple()) * 1000)
            x_data.append(day)

            for exchange in exchanges:
                for pair in exchange.pairs.all():
                    balance = Balance.objects.filter(
                        pair=pair
                    ).filter(
                        time_added__gte=midnight
                    ).filter(
                        time_added__lt=tomorrow
                    ).aggregate(
                        Avg('base_amount')
                    ).aggregate(
                        Avg('quote_amount')
                    )

                    if currency_totals[exchange][pair.base_currency] == Decimal(0):
                        currency_totals[exchange][pair.base_currency] = balance['base_amount__avg']  # noqa

                    if currency_totals[exchange][pair.quote_currency] == Decimal(0):
                        currency_totals[exchange][pair.quote_currency] = balance['quote_amount__avg']  # noqa

                # for currency in currency_totals[exchange]:
                #     if currency.get_usd_value:
                        
                # y_data[coin.unit_code].append(
                #     info['money_supply__avg']
                #     if info ['money_supply__avg'] is not None
                #     else 0
                # )

           # low_date = tomorrow


class CirculatingChart(View):
    @staticmethod
    def get(request):
        x_data = []
        y_data = {}

        low_date = Info.objects.all().aggregate(
            Min('time_added')
        )
        low_date = low_date['time_added__min']
        max_date = Info.objects.all().aggregate(
            Max('time_added')
        )
        max_date = max_date['time_added__max']

        coins = list(connection.tenant.coins.all())

        for coin in coins:
            y_data[coin.unit_code] = []

        while low_date < max_date:
            midnight = make_aware(
                datetime.datetime(
                    low_date.year,
                    low_date.month,
                    low_date.day,
                    0,
                    0,
                    0
                )
            )
            tomorrow = midnight + datetime.timedelta(days=1)
            day = int(time.mktime(tomorrow.timetuple()) * 1000)
            x_data.append(day)

            for coin in coins:
                info = Info.objects.filter(
                    unit=coin.unit_code
                ).filter(
                    time_added__gte=midnight
                ).filter(
                    time_added__lt=tomorrow
                ).aggregate(
                    Avg('money_supply')
                )
                y_data[coin.unit_code].append(
                    info['money_supply__avg']
                    if info ['money_supply__avg'] is not None
                    else 0
                )

            low_date = tomorrow

        series_data = {'x': x_data}
        index = 1

        for coin in coins:
            series_data['y{}'.format(index)] = y_data[coin.unit_code]
            series_data['name{}'.format(index)] = 'Circulating {}'.format(coin.name)
            series_data['extra{}'.format(index)] = {
                "tooltip": {
                    "y_start": "There are ",
                    "y_end": " circulating"
                },
                "date_format": "%d %b %Y %H:%M:%S %p"
            }
            index += 1

        chart_data = {
            'chart_type': "lineChart",
            'name': 'Circulating Currency',
            'series_data': series_data,
            'extra': {
                'x_is_date': True,
                'color_category': 'category10',
            },

        }

        return render(request, 'charts/circulating_currency.html', chart_data)

