import json

import os
from django.shortcuts import render
from django.views import View

from django.conf import settings


class Funds(View):
    @staticmethod
    def get(request):
        nodes = json.dumps(
            json.load(
                open(
                    os.path.join(
                        settings.BASE_DIR,
                        'charts/data/nodes.json'
                    )
                )
            )
        )
        edges = json.dumps(
            json.load(
                open(
                    os.path.join(
                        settings.BASE_DIR,
                        'charts/data/edges.json'
                    )
                )
            )
        )
        return render(request, 'charts/funds.html', {'nodes': nodes, 'edges': edges})
