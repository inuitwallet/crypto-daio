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

    def handle_tx(self, tx, base_address=None):
        if tx in scanned_transactions:
            return

        if tx.index == 1:
            return

        if not tx.block:
            return

        scanned_transactions.append(tx)

        logger.info(tx.tx_id)

        # add the Tx to the nodes
        if not any(node['id'] == tx.tx_id for node in nodes):
            nodes.append({
                'id': tx.tx_id,
                'shape': 'dot',
                'title': '{}'.format(tx),
                'size': 3
            })

        if base_address:
            edges.append({
                'from': base_address,
                'to': tx.tx_id,
                'color': 'grey',
                'arrows': 'middle'
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
                    'title': 'Address'
                })
            edges.append({
                'from': input_address,
                'to': tx.tx_id,
                'value': address_inputs.get(input_address, 0) / 100000000,
                'title': address_inputs.get(input_address, 0) / 100000000,
                'color': '#2cf948',
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
                    'title': 'Address'
                })
            edges.append({
                'from': tx.tx_id,
                'to': address,
                'value': output_totals['unspent'].get(address, 0) / 100000000,
                'title': output_totals['unspent'].get(address, 0) / 100000000,
                'color': '#d86868',
                'arrows': 'middle'
            })

        for transaction in output_totals['spent']:
            # add the Tx to the nodes
            if not any(node['id'] == transaction.tx_id for node in nodes):
                nodes.append({
                    'id': transaction.tx_id,
                    'shape': 'dot',
                    'title': '{}'.format(transaction),
                    'size': 3
                })
            edges.append({
                'from': tx.tx_id,
                'to': transaction.tx_id,
                'value': output_totals['spent'].get(transaction, 0) / 100000000,
                'title': output_totals['spent'].get(transaction, 0) / 100000000,
                'color': '#f4a84b',
                'arrows': 'middle'
            })

    def handle(self, *args, **options):
        """
        investigate the losses by tracking activity through the blockchain
        :param args:
        :param options:
        :return:
        """
        # 1 At which date was a transaction made from a compromised to target address
        # get all transaction that have a compromised address as an input
        # of those look at only the ones that have a compromised address as an output
        # earliest 1 wins

        # 2 How much per compromised address was sent to a target address?
        # using transactions from 1. look at amounts input and output

        # 3 How much remains at each target address and each compromised address?
        # just balances

        # get the transactions that have a compromised address as an input
        transactions = Transaction.objects.filter(
            input__previous_output__address__address__in=COMPROMISED_ADDRESSES
        ).exclude(
            block=None
        ).filter(
            output__address__address__in=TARGET_ADDRESSES
        ).order_by(
            'time'
        )
        earliest_tx = transactions[0]
        logger.info('{} is the earliest transaction'.format(earliest_tx))

        # using these transactions get the amounts input and output
        for transaction in transactions:
            logger.info('In transaction {}'.format(transaction))
            address_inputs = transaction.address_inputs
            for address in address_inputs:
                if address not in COMPROMISED_ADDRESSES:
                    continue
                logger.info(
                    '\t{} went in from {}'.format(address_inputs.get(address, 0), address)
                )
            address_outputs = transaction.address_outputs
            for address in address_outputs:
                if address not in TARGET_ADDRESSES:
                    continue
                logger.info(
                    '\t{} came out to {}'.format(address_outputs.get(address, 0), address)
                )

        # then report on balances:
        for address in TARGET_ADDRESSES + COMPROMISED_ADDRESSES:
            logger.info('{} has current balance of {}'.format(address, address.balance))




