import datetime
import time
from django.db import connection
from django.shortcuts import render
from django.utils.timezone import make_aware
from django.views import View

from charts.models import Balance, CurrencyValue, WatchedAddress, WatchedAddressBalance


class NAVChart(View):
    @staticmethod
    def get(request):
        # # get GET data to set chart boundaries
        # span = int(request.GET.get('span', 43200))
        # interval = int(request.GET.get('interval', 1440))
        #
        # # instantiate data structures
        # value_data = {}
        # balance_types = []
        #
        # # get the start date
        # start_date = datetime.datetime.now() - datetime.timedelta(minutes=span)
        # date = make_aware(
        #         datetime.datetime(start_date.year, start_date.month, start_date.day)
        #     )
        #
        # # populate data structures
        # while date <= make_aware(datetime.datetime.now()):
        #     value_data[date] = {}
        #
        #     # exchange balances
        #     for exchange in connection.tenant.exchanges.all():
        #         value_data[date][exchange] = {}
        #
        #         for pair in exchange.pairs.all():
        #             balance = Balance.objects.get_closest_to(pair, date)
        #
        #             if pair.base_currency not in value_data[date][exchange]:
        #                 balance_type = (exchange, pair.base_currency)
        #                 if balance_type not in balance_types:
        #                     balance_types.append(balance_type)
        #
        #                 base_amount = balance.base_amount
        #                 if pair.base_currency.get_usd_value:
        #                     base_value = CurrencyValue.objects.get_closest_to(
        #                         pair.base_currency,
        #                         date
        #                     ).usd_value
        #                     base_amount *= base_value
        #                 value_data[date][exchange][pair.base_currency] = base_amount
        #
        #             if pair.quote_currency not in value_data[date][exchange]:
        #                 balance_type = (exchange, pair.quote_currency)
        #                 if balance_type not in balance_types:
        #                     balance_types.append(balance_type)
        #
        #                 quote_amount = balance.quote_amount
        #                 if pair.quote_currency.get_usd_value:
        #                     quote_value = CurrencyValue.objects.get_closest_to(
        #                         pair.quote_currency,
        #                         date
        #                     ).usd_value
        #                     quote_amount *= quote_value
        #                 value_data[date][exchange][pair.quote_currency] = quote_amount
        #
        #     # watched addresses
        #     for address in WatchedAddress.objects.all():
        #         closest_balance = WatchedAddressBalance.objects.get_closest_to(
        #             address.address,
        #             date
        #         )
        #
        #         balance = closest_balance.balance
        #         if address.currency.get_usd_value:
        #             value = CurrencyValue.objects.get_closest_to(
        #                 address.currency,
        #                 date
        #             ).usd_value
        #             balance *= value
        #
        #         value_data[date][address.address] = balance
        #
        #     date += datetime.timedelta(minutes=interval)
        #
        # x_values = sorted([date for date in value_data])
        # series_data = {
        #     'x': [int(time.mktime(date.timetuple()) * 1000) for date in x_values]
        # }
        # index = 1
        # for balance_type in balance_types:
        #     series_data['y{}'.format(index)] = []
        #     for date in x_values:
        #         series_data['y{}'.format(index)].append(
        #             float(value_data[date][balance_type[0]][balance_type[1]])
        #         )
        #     series_data['name{}'.format(index)] = '{}@{} value'.format(
        #         balance_type[1].code,
        #         balance_type[0]
        #     )
        #     series_data['extra{}'.format(index)] = {
        #         "tooltip": {
        #             "y_start": "NAV = ",
        #             "y_end": "."
        #         },
        #         "date_format": "%d %b %Y %H:%M:%S %p"
        #     }
        #     index += 1
        #
        # for address in WatchedAddress.objects.all():
        #     series_data['y{}'.format(index)] = []
        #     for date in x_values:
        #         series_data['y{}'.format(index)].append(
        #             float(value_data[date][address.address])
        #             if value_data[date][address.address]
        #             else float(0)
        #         )
        #     series_data['name{}'.format(index)] = '{} balance'.format(
        #         address.address
        #     )
        #     series_data['extra{}'.format(index)] = {
        #         "tooltip": {
        #             "y_start": "NAV = ",
        #             "y_end": "."
        #         },
        #         "date_format": "%d %b %Y %H:%M:%S %p"
        #     }
        #     index += 1
        #
        # chart_data = {
        #     'chart_type': "stackedAreaChart",
        #     'name': 'Historical NAV in USD',
        #     'series_data': series_data,
        #     "date_format": "%d %b %Y %H:%M:%S %p",
        #     'extra': {
        #         'x_is_date': True,
        #         'x_axis_format': "%d %b %Y %H:%M:%S %p",
        #         'color_category': 'category10',
        #         'margin_left': 100,
        #         'margin_right': 100,
        #         'margin_bottom': 150,
        #         'use_interactive_guideline': True,
        #         'xAxis_rotateLabel': 45,
        #         'show_controls': False,
        #     },
        #     'chain': connection.tenant,
        #     'span': span,
        #     'interval': interval
        # }
        return render(request, 'charts/usd_nav.html', {'chain': connection.tenant})

