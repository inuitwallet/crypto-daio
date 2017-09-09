import csv
import json
import logging

from django.core.management import BaseCommand
from django.utils import timezone

from blocks.models import Address, TxInput, Transaction

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()

COMPROMISED_ADDRESSES = [
    'SSajkovCPXwdw46nyJ7vpTDkwtRZJzyY2z',
    # 'SNf4uyshit1fj8dWKVxHsKTgTrNR61RskY',
    # 'SQTHenWRCF7tZQb5RQAbf3pVYN3Jq5RET4',
    # 'ShGVUEJpyZBTgK6V5ZzBorv899R1LP7pqm',
    # 'SNdbH9sUJ8z33iE8oNBCwCLfwP9tafyZh3',
    # 'Sb84GHDPxy1dzE4VttDTrLwYLzLw4hEDUV',
    # 'SUgGG6PYXeoXtrUU85rViuWbxsVczwQX7i',
    # 'SRcyHX5JE1tprmtUNswHFsgWqwciwkqigk',
    # 'SMv2C8x41mtkZvv5wNejdqSsBQPPTfPEDj',
    # 'SQGuknAk53MpBMy9fuX632Kqi8FWoNMQ2v',
    # 'SYrndApJNq5JrXGu83NQuzb3PHQoaeEwx8',
    # 'SXQcdc5THvdUAdfmK4NEYQpvqANwz4iBHg',
    # 'SeTPb7fj6PLn2E4aMa5TbR83Pw6MSs37fM',
]

TARGET_ADDRESSES = [
    'SfhbL4Hmkvh8t79wkFEotnGqf64GvvB7HV',
    'Sh5okqoxnFoiCVAJEdzfxzHqSyunriVPmp',
    'SUGfxGPyCgaNg3FjXjcpMwtco1CTNbRSwG',
    'SeSuCVYzdPT1Biw9cfuK4mHYGTeihqY7Cq',
    'SY3mR9hhtN6V4JVG8nf466SMr6Vx2asDSp',
    'SVZ9C4D78Xmca7S4edFoghJB6znVcjBf9s',
    'ST2FF2LybChMcpj5dywaLTG2P4pezvspiJ',
    'SV3ZNwQ9CCDaHFb3BjwviUZzq1sDDycDtH',
    'SMgrPVqXaVfcrFgMFesJZT37b4VBohWxqr',
    'Se3FvyRoshq6zjGbiWLYYAKAJnP3kH4Xvj',
    'SUGCjFktPEdXBquPJdSemuxZFy4AxvbXH4',
    'Sg6aYkT7MP2R6FttKoKAPXqtTw1CHEzkZN',
    'SNQ4BWMpiumVtTEmrW4xAYfbJFhxdHZBxz',
    'STWUi4iSgpAwJrycwrurn1j7DTS18w7ZDN',
    'SickUboc7GTJK7TxF7vfYnunFLk81NLr9p',
    'SeDCHvv8VQx1dsZFBJRJEmcjTTEvKU1QxH',
    'Sf8xcBTzjxHV7518BE3xuQqHTzTr9BKTfr',
    'SNbMQJnVDymEvE2vpyHfqdKzedjekXsGQi',
    'ScDYXcJc4TShVLcKBmgRq9rz6ZvqfLrAkv',
]

nodes = []
edges = []


class Command(BaseCommand):
    @staticmethod
    def get_transactions(address):
        txs = Transaction.objects.filter(
            input__previous_output__address=address
        ).exclude(
            index=1
        ).exclude(
            output__address__address__in=TARGET_ADDRESSES
        ).order_by(
            'time'
        )

        distinct = []
        for tx in txs:
            if tx in distinct:
                continue
            distinct.append(tx)

        return distinct

    def handle_tx(self, tx):
        logger.info('handling transaction {}'.format(tx.tx_id))

        # add the Tx to the nodes
        if not any(node['id'] == tx.tx_id[:6] for node in nodes):
            nodes.append({'id': tx.tx_id[:6], 'label': tx.tx_id, 'hidden': True})

        address_inputs = tx.address_inputs
        for input_address in address_inputs:
            # for each input add an edge from the address to the tx.
            # Add the address if it doesn't exist
            if not any(node['id'] == input_address for node in nodes):  # noqa
                nodes.append({
                    'id': input_address,
                    'label': input_address,
                    'color': 'red' if input_address in TARGET_ADDRESSES else 'blue',
                    'shape': 'square'
                })
            edges.append({
                'from': input_address,
                'to': tx.tx_id[:6],
                'value': address_inputs.get(input_address, 0) / 100000000,
                'arrows': 'middle'
            })

        address_outputs = tx.address_outputs
        for output_address in address_outputs:
            # for each output add an edge from the address to the tx.
            # Add the address if it doesn't exist
            if not any(node['id'] == output_address for node in nodes):  # noqa
                nodes.append({
                    'id': output_address,
                    'label': output_address,
                    'color': 'red' if output_address in TARGET_ADDRESSES else 'blue',
                    'shape': 'square'
                })
            edges.append({
                'from': tx.tx_id[:6],
                'to': output_address,
                'value': address_outputs.get(output_address, 0) / 100000000,
                'arrows': 'middle',
                'title': tx.time
            })

        # for tx_output in tx.outputs.all():
        #     try:
        #         if tx_output.input:
        #             self.handle_tx(tx_output.input.transaction)
        #     except TxInput.DoesNotExist:
        #         pass

    def handle(self, *args, **options):
        """
        investigate the losses by tracking activity through the blockchain
        :param args:
        :param options:
        :return:
        """
        for address in COMPROMISED_ADDRESSES:
            logger.info('working on {}'.format(address))
            # add the address to the nodes
            nodes.append({
                'id': address,
                'label': address,
                'color': 'green',
                'shape': 'square'
            })
            a = Address.objects.get(address=address)
            txs = self.get_transactions(a)

            for tx in txs:
                self.handle_tx(tx)

        json.dump(nodes, open('nodes.json', 'w+'))
        json.dump(edges, open('edges.json', 'w+'))
