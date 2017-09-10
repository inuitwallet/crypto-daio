import json
import logging

import os

from django.conf import settings
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

scanned_transactions = []


class Command(BaseCommand):
    @staticmethod
    def get_transactions(address):
        txs = Transaction.objects.distinct(
            'tx_id'
        ).filter(
            input__previous_output__address=address
        ).exclude(
            index=1
        ).exclude(
            output__address__address__in=TARGET_ADDRESSES
        ).exclude(
            block=None
        ).order_by(
            'tx_id'
        )

        return sorted(txs, key=lambda tx: tx.total_input, reverse=True)

    def handle_tx(self, tx):
        if tx.tx_id[:6] in scanned_transactions:
            return

        if tx.index == 1:
            return

        if not tx.block:
            return

        scanned_transactions.append(tx.tx_id[:6])

        logger.info(tx.tx_id)

        # add the Tx to the nodes
        if not any(node['id'] == tx.tx_id[:6] for node in nodes):
            nodes.append({
                'id': tx.tx_id[:6],
                'shape': 'dot',
                'title': '{}'.format(tx),
                'size': 3
            })

        address_inputs = tx.address_inputs
        for input_address in address_inputs:
            # for each input add an edge from the address to the tx.
            # Add the address if it doesn't exist
            if not any(node['id'] == input_address for node in nodes):  # noqa
                nodes.append({
                    'id': input_address,
                    'label': input_address,
                    'color': '#dd6161' if input_address in TARGET_ADDRESSES else '#92d9e5',  # noqa
                })
            edges.append({
                'from': input_address,
                'to': tx.tx_id[:6],
                'value': address_inputs.get(input_address, 0) / 100000000,
                'title': address_inputs.get(input_address, 0) / 100000000,
                'color': 'grey',
                'arrows': 'middle'
            })

        output_totals = {'spent': {}, 'unspent': {}}
        for tx_output in tx.outputs.all():
            try:
                if tx_output.input:
                    if tx_output.input.transaction not in output_totals['spent']:
                        output_totals['spent'][tx_output.input.transaction] = 0
                    output_totals['spent'][tx_output.input.transaction] += tx_output.value
            except TxInput.DoesNotExist:
                if not tx_output.address:
                    continue
                if tx_output.address.address not in output_totals['unspent']:
                    output_totals['unspent'][tx_output.address.address] = 0
                output_totals['unspent'][tx_output.address.address] += tx_output.value

        for address in output_totals['unspent']:
            if not any(node['id'] == address for node in nodes):
                nodes.append({
                    'id': address,
                    'label': address,
                    'color': '#dd6161' if address in TARGET_ADDRESSES else '#92d9e5',
                })
            edges.append({
                'from': tx.tx_id[:6],
                'to': address,
                'value': output_totals['unspent'].get(address, 0) / 100000000,
                'title': output_totals['unspent'].get(address, 0) / 100000000,
                'color': 'grey',
                'arrows': 'middle'
            })

        for transaction in output_totals['spent']:
            # add the Tx to the nodes
            if not any(node['id'] == transaction.tx_id[:6] for node in nodes):
                nodes.append({
                    'id': transaction.tx_id[:6],
                    'shape': 'dot',
                    'title': '{}'.format(tx),
                    'size': 3
                })
            edges.append({
                'from': tx.tx_id[:6],
                'to': transaction.tx_id[:6],
                'value': output_totals['spent'].get(transaction, 0) / 100000000,
                'title': output_totals['spent'].get(transaction, 0) / 100000000,
                'color': 'grey',
                'arrows': 'middle'
            })
            self.handle_tx(transaction)

    def handle(self, *args, **options):
        """
        investigate the losses by tracking activity through the blockchain
        :param args:
        :param options:
        :return:
        """
        for address in COMPROMISED_ADDRESSES:
            logger.info('adding origin node {}'.format(address))
            if not any(node['id'] == address for node in nodes):
                nodes.append({
                    'id': address,
                    'label': address,
                    'color': '#89ff91',
                })

        try:
            for address in COMPROMISED_ADDRESSES:
                logger.info('working on {}'.format(address))
                a = Address.objects.get(address=address)
                txs = self.get_transactions(a)

                for tx in txs:
                    logger.info('handling direct transaction {}'.format(tx))
                    self.handle_tx(tx)

            json.dump(nodes, open(
                os.path.join(
                    settings.BASE_DIR,
                    'charts/data/nodes.json'
                ),
                'w+'
            ))
            json.dump(edges, open(
                os.path.join(
                    settings.BASE_DIR,
                    'charts/data/edges.json'
                ),
                'w+'
            ))

            logger.info('Finished')

        except KeyboardInterrupt:
            json.dump(nodes, open(
                os.path.join(
                    settings.BASE_DIR,
                    'charts/data/nodes.json'
                ),
                'w+'
            ))
            json.dump(edges, open(
                os.path.join(
                    settings.BASE_DIR,
                    'charts/data/edges.json'
                ),
                'w+'
            ))

            logger.info('Written')
