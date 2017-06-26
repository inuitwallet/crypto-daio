import datetime

from decimal import Decimal
from operator import itemgetter

from django.db import connection
from django.shortcuts import render
from django.views import View

from charts.models import Order, CurrencyValue


class CurrentLiquidityChart(View):
    """
    Get open orders and graph them
    x axis = price
    y axis = amount in usd
    line for buy, line for sell for each pair/exchange
    """

    @staticmethod
    def get(request):
        data = {'BUY': [], 'SELL': []}
        pairs = []
        x_values = []
        for exchange in connection.tenant.exchanges.all():
            for pair in exchange.pairs.all():
                pairs.append(pair)
                # fetch uds values
                quote_value = None
                if pair.quote_currency.get_usd_value:
                    quote_value = CurrencyValue.objects.get_closest_to(
                        pair.quote_currency,
                        datetime.datetime.now()
                    ).usd_value

                base_value = None
                if pair.base_currency.get_usd_value:
                    base_value = CurrencyValue.objects.get_closest_to(
                        pair.base_currency,
                        datetime.datetime.now()
                    ).usd_value

                # get open buy orders
                buy_aggregate = Decimal(0)
                for order in Order.objects.filter(
                    pair=pair,
                    open=True,
                    order_type='BUY'
                ).order_by('-rate'):
                    rate = (order.rate * base_value) if base_value else order.rate
                    amount = (order.amount * quote_value) if quote_value else order.amount
                    buy_aggregate += amount
                    data['BUY'].append(
                        {'rate': rate, 'amount': buy_aggregate, 'pair': pair}
                    )
                    x_values.append(float(rate))

                sell_aggregate = Decimal(0)
                for order in Order.objects.filter(
                        pair=pair,
                        open=True,
                        order_type='SELL'
                ).order_by('rate'):
                    rate = (order.rate * base_value) if base_value else order.rate
                    amount = (order.amount * quote_value) if quote_value else order.amount
                    sell_aggregate += amount
                    data['SELL'].append(
                        {'rate': rate, 'amount': sell_aggregate, 'pair': pair}
                    )
                    x_values.append(float(rate))

        x_values.append(float(1.0))

        y_data = {'BUY': {}, 'SELL': {}}

        for pair in pairs:
            y_data['BUY'][pair] = []
            y_data['SELL'][pair] = []

        for rate in sorted(x_values):
            buy_order = next(
                (item for item in data['BUY'] if float(item['rate']) == rate),
                None
            )
            if buy_order:
                for pair in pairs:
                    if buy_order['pair'] == pair:
                        y_data['BUY'][pair].append(float(buy_order['amount']))
                    else:
                        y_data['BUY'][pair].append(float(0.0))
            else:
                for pair in pairs:
                    y_data['BUY'][pair].append(float(0.0))

            sell_order = next(
                (item for item in data['SELL'] if float(item['rate']) == rate),
                None
            )
            if sell_order:
                for pair in pairs:
                    if sell_order['pair'] == pair:
                        y_data['SELL'][pair].append(float(sell_order['amount']))
                    else:
                        y_data['SELL'][pair].append(float(0.0))
            else:
                for pair in pairs:
                    y_data['SELL'][pair].append(float(0.0))

        for pair in y_data['BUY']:
            new_data = []
            max_value = float(0.0)
            for value in reversed(y_data['BUY'][pair]):
                if value > max_value:
                    max_value = value
                if value == float(0.0):
                    new_data.append(max_value)
                else:
                    new_data.append(value)
            y_data['BUY'][pair] = list(reversed(new_data))

        for pair in y_data['SELL']:
            new_data = []
            max_value = float(0.0)
            for value in y_data['SELL'][pair]:
                if value > max_value:
                    max_value = value
                if value == float(0.0):
                    new_data.append(max_value)
                else:
                    new_data.append(value)
            y_data['SELL'][pair] = new_data

        series_data = {'x': sorted(x_values)}
        index = 1

        for side in ['BUY', 'SELL']:
            for pair in pairs:
                series_data['y{}'.format(index)] = y_data[side][pair]
                series_data['name{}'.format(index)] = '{} {} Orders'.format(pair, side)
                index += 1

        chart_data = {
            'chart_type': "stackedAreaChart",
            'name': 'Current Liquidity',
            'series_data': series_data,
            'extra': {
                'x_axis_format': '.8f',
                'color_category': 'category10',
                'margin_left': 100,
                'show_controls': False,
                'use_interactive_guideline': True,
            },
            'buy_orders': Order.objects.filter(
                open=True,
                order_type='BUY'
            ).order_by(
                '-rate'
            ),
            'sell_orders': Order.objects.filter(
                open=True,
                order_type='SELL'
            ).order_by(
                'rate'
            ),
            'chain': connection.tenant
        }

        return render(request, 'charts/current_liquidity.html', chart_data)
