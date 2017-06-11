import datetime
import random
import time

from django.db import connection
from django.shortcuts import render_to_response
from django.views import View

from blocks.models import Info


class Charts(View):
    @staticmethod
    def get(request):
        # get circulating currency
        x_data = []
        coin_data = {}

        for coin in connection.tenant.coins.all():
            coin_data[coin.unit_code] = []

        for info_object in Info.objects.all().order_by('time_added'):
            info_date = int(time.mktime(info_object.time_added.timetuple())*1000)
            x_data.append(info_date)
            coin_data[info_object.unit].append(float(info_object.money_supply))

        print(x_data)
        print(coin_data)

        tooltip_date = "%d %b %Y %H:%M:%S %p"
        extra_serie = {
            "tooltip": {
                "y_start": "There are ",
                "y_end": " circulating"
            },
            "date_format": tooltip_date
        }
        chart_data = {
            'x': x_data
        }
        index = 1
        for coin in connection.tenant.coins.all():
            chart_data['name{}'.format(index)] = 'Circulating {}'.format(coin.name)
            chart_data['y{}'.format(index)] = coin_data[coin.unit_code]
            chart_data['extra{}'.format(index)] = extra_serie
            index += 1
        data = {
            'charttype': "lineWithFocusChart",
            'chartdata': chart_data,
            'extra': {
                'x_is_date': True,

            }
        }
        return render_to_response('charts/linewithfocuschart.html', data)

