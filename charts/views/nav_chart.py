from django.db import connection
from django.shortcuts import render
from django.views import View


class NAVChart(View):
    @staticmethod
    def get(request):
        return render(request, 'charts/usd_nav.html', {'chain': connection.tenant})
