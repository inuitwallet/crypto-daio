from django.db import connection
from django.shortcuts import render
from django.views import View


class AngularExplorer(View):
    @staticmethod
    def get(request):
        chain = connection.tenant
        return render(request, "explorer-angular.html", {"chain": chain})
