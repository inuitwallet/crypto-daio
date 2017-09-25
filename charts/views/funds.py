from django.db import connection
from django.shortcuts import render
from django.views import View


class Funds(View):
    @staticmethod
    def get(request):
        nodes = [
            {
                'id': 'Address_{}'.format(address),
                'label': address,
                'color': '#89ff91',
                'title': 'Address_{}'.format(address),
            } for address in [
                'SSajkovCPXwdw46nyJ7vpTDkwtRZJzyY2z',
                'SNf4uyshit1fj8dWKVxHsKTgTrNR61RskY',
                'SQTHenWRCF7tZQb5RQAbf3pVYN3Jq5RET4',
                'ShGVUEJpyZBTgK6V5ZzBorv899R1LP7pqm',
                'SNdbH9sUJ8z33iE8oNBCwCLfwP9tafyZh3',
                'Sb84GHDPxy1dzE4VttDTrLwYLzLw4hEDUV',
                'SUgGG6PYXeoXtrUU85rViuWbxsVczwQX7i',
                'SRcyHX5JE1tprmtUNswHFsgWqwciwkqigk',
                'SMv2C8x41mtkZvv5wNejdqSsBQPPTfPEDj',
                'SQGuknAk53MpBMy9fuX632Kqi8FWoNMQ2v',
                'SYrndApJNq5JrXGu83NQuzb3PHQoaeEwx8',
                'SXQcdc5THvdUAdfmK4NEYQpvqANwz4iBHg',
                'SeTPb7fj6PLn2E4aMa5TbR83Pw6MSs37fM',
                #'SXXFagQLbM7QLfMKEj9HVhzkXiAHxmBaB1'
            ]
        ]
        return render(
            request,
            'charts/funds.html',
            {
                'nodes': nodes,
                'edges': [],
                'chain': connection.tenant
            }
        )
