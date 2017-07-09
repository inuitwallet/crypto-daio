import datetime
import time
from decimal import Decimal
from django.db import connection
from django.shortcuts import render
from django.utils.timezone import make_aware
from django.views import View

from charts.models import Balance, CurrencyValue


class NAVChart(View):
    @staticmethod
    def get(request):
        totals = {}
        balances = {}
        value_date = datetime.datetime.now() - datetime.timedelta(days=30)
        while value_date <= datetime.datetime.now():
            date = make_aware(
                datetime.datetime(value_date.year, value_date.month, value_date.day)
            )
            totals[date] = Decimal(0)
            balances[date] = {}
            value_date += datetime.timedelta(days=1)

        scanned_currencies = {}
        for exchange in connection.tenant.exchanges.all():
            scanned_currencies[exchange] = {}
            for pair in exchange.pairs.all():
                for date_time in totals:
                    scanned_currencies[exchange][date_time] = []
                    balance = Balance.objects.get_closest_to(pair, date_time)

                    base_amount = balance.base_amount
                    base_value = 1
                    if pair.base_currency.get_usd_value:
                        base_value = CurrencyValue.objects.get_closest_to(
                            pair.base_currency,
                            datetime.datetime.now()
                        ).usd_value
                        base_amount *= base_value

                    quote_amount = balance.quote_amount
                    quote_value = 1
                    if pair.quote_currency.get_usd_value:
                        quote_value = CurrencyValue.objects.get_closest_to(
                            pair.quote_currency,
                            datetime.datetime.now()
                        ).usd_value
                        quote_amount *= quote_value

                    if pair.base_currency not in scanned_currencies[exchange][date_time]:
                        totals[date_time] += base_amount
                        scanned_currencies[exchange][date_time].append(
                            pair.base_currency
                        )

                    if pair.quote_currency not in scanned_currencies[exchange][date_time]:
                        totals[date_time] += quote_amount
                        scanned_currencies[exchange][date_time].append(
                            pair.quote_currency
                        )

                    balances[date_time] = {
                        'quote': pair.quote_currency,
                        'amount': quote_amount,
                        'value': quote_value
                    }

        x_values = sorted([date for date in totals])

        chart_data = {
            'chart_type': "lineChart",
            'name': '30 day historical NAV on exchanges in USD ',
            'series_data': {
                'x': [int(time.mktime(date.timetuple()) * 1000) for date in x_values],
                'y1': [float(totals.get(date)) for date in x_values],
                'name1': 'NAV on exchange in USD',
                'extra1': {
                    "tooltip": {
                        "y_start": "NAV = ",
                        "y_end": "."
                    },
                    "date_format": "%d %b %Y %H:%M:%S %p"
                }
            },
            'extra': {
                'x_is_date': True,
                'color_category': 'category10',
                'margin_left': 100,
                'use_interactive_guideline': True,
            },
            'chain': connection.tenant
        }
        print(chart_data)
        return render(request, 'charts/30_day_nav.html', chart_data)

