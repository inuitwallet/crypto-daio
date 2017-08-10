from django.db import connection
from django.shortcuts import render
from django.views import View

from charts.urls import urlpatterns


class ChartsView(View):
    @staticmethod
    def get(request):
        urls = []
        for url_pattern in urlpatterns:
            urls.append((url_pattern.name.replace('_', ' ').title(), url_pattern.name))
        return render(
            request,
            'explorer/chart_menu.html',
            {
                'urls': urls,
                'chain': connection.tenant
            }
        )
