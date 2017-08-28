import datetime
import time
from django.db import connection
from django.shortcuts import render
from django.views import View

from blocks.models import Peer, Info, Orphan


class HealthView(View):

    @staticmethod
    def get(request):
        # get the latest info object
        info = Info.objects.all().order_by('-time_added').first()
        # calculate the peers distance from our latest block
        peers = Peer.objects.all().order_by('-height')
        for peer in peers:
            peer.height_diff = peer.height - info.max_height

        # calculate when we should expect the next block

        # get 30 day difficulty
        times = []
        difficulties = []
        orphans = []
        get_date = datetime.datetime.now() - datetime.timedelta(days=30)
        while get_date < datetime.datetime.now():
            info = Info.objects.get_closest_to(
                target=get_date
            )
            times.append(info.time_added)
            difficulties.append(info.difficulty)

            orphans.append(
                Orphan.objects.filter(
                    date_time__gte=get_date - datetime.timedelta(days=1),
                    date_time__lt=get_date
                ).count()
            )

            get_date += datetime.timedelta(days=1)

        orphan_chart_data = {
            'chart_type': "lineChart",
            'name': '30 Day Difficulty',
            'series_data': {
                'x': [int(time.mktime(date.timetuple()) * 1000) for date in times],
                'y1': [float(orphan_count) for orphan_count in orphans],
                'name1': 'Number of Orphan blocks',
                'extra1': {
                    "tooltip": {
                        "y_start": "There were ",
                        "y_end": " Orphan blocks"
                    },
                    "date_format": "%d %b %Y %H:%M:%S %p"
                }
            },
            "date_format": "%d %b %Y %H:%M:%S %p",
            'extra': {
                'x_is_date': True,
                'x_axis_format': "%d %b %Y",
                'y_axis_format': "5",
                'color_category': 'category10',
                'margin_left': 100,
                'margin_right': 100,
                'margin_bottom': 150,
            }
        }

        difficulty_chart_data = {
            'chart_type': "lineChart",
            'name': '30 Day Difficulty',
            'series_data': {
                'x': [int(time.mktime(date.timetuple()) * 1000) for date in times],
                'y1': [float(difficulty) for difficulty in difficulties],
                'name1': 'Difficulty',
                'extra1': {
                    "tooltip": {
                        "y_start": "The network difficulty was ",
                        "y_end": ""
                    },
                    "date_format": "%d %b %Y %H:%M:%S %p"
                }
            },
            "date_format": "%d %b %Y %H:%M:%S %p",
            'extra': {
                'x_is_date': True,
                'x_axis_format': "%d %b %Y",
                'y_axis_format': "5",
                'color_category': 'category10',
                'margin_left': 100,
                'margin_right': 100,
                'margin_bottom': 150,
            }
        }

        return render(
            request,
            'explorer/health.html',
            {
                'chain': connection.tenant,
                'peers': peers,
                'orphan_chart_data': orphan_chart_data,
                'difficulty_chart_data': difficulty_chart_data,
            }
        )