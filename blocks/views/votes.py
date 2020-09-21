from django.db import connection
from django.shortcuts import render
from django.views import View


class GrantView(View):
    @staticmethod
    def get(request):
        return render(request, "explorer/grants.html", {"chain": connection.tenant})


class MotionView(View):
    @staticmethod
    def get(request):
        return render(request, "explorer/motions.html", {"chain": connection.tenant})
