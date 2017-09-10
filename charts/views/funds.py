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
                        'charts/data/nodes_SQTHenWRCF7tZQb5RQAbf3pVYN3Jq5RET4.json'
                    )
                )
            )
        )
        edges = json.dumps(
            json.load(
                open(
                    os.path.join(
                        settings.BASE_DIR,
                        'charts/data/edges_SQTHenWRCF7tZQb5RQAbf3pVYN3Jq5RET4.json'
                    )
                )
            )
        )
        return render(request, 'charts/funds.html', {'nodes': nodes, 'edges': edges})
