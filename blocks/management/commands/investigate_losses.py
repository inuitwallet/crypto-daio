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


class Command(BaseCommand):
    @staticmethod
    def gather_tx_data():
        with open('losses.csv', 'w+') as losses_file:
            loss_writer = csv.writer(losses_file)
            loss_writer.writerow(['Date', 'Block', 'From', 'To', 'Input', 'Outputs'])

            for address in COMPROMISED_ADDRESSES:
                logger.info('looking for {} data'.format(address))
                try:
                    addr = Address.objects.get(address=address)
                except Address.DoesNotExist:
                    logger.error('{} does not exist'.format(address))
                    continue

                matched_txs = []
                for output in addr.outputs.all():
                    try:
                        if output.input.transaction in matched_txs:
                            continue

                        matched_txs.append(output.input.transaction)
                        in_values = output.input.transaction.address_inputs
                        out_values = output.input.transaction.address_outputs

                        for value_address in out_values:
                            if value_address in TARGET_ADDRESSES:
                                logger.info(
                                    '{} moved {} from {} to {} on {}'.format(
                                        output.input.transaction,
                                        out_values[value_address],
                                        address,
                                        value_address,
                                        output.input.transaction.time
                                    )
                                )
                                loss_writer.writerow(
                                    [
                                        output.input.transaction.time,
                                        output.input.transaction.block.height,
                                        address,
                                        value_address,
                                        in_values[address],
                                        out_values[value_address]
                                    ]
                                )
                    except TxInput.DoesNotExist:
                        continue

    @staticmethod
    def get_balances():
        with open('balances.csv', 'w+') as balances_csv:
            balance_writer = csv.writer(balances_csv)
            balance_writer.writerow(['Address', 'Balance'])
            for address in COMPROMISED_ADDRESSES + TARGET_ADDRESSES:
                logger.info('getting balance for {}'.format(address))
                try:
                    addr = Address.objects.get(address=address)
                except Address.DoesNotExist:
                    logger.error('{} does not exist'.format(address))
                    continue
                balance_writer.writerow([addr, addr.balance])

    @staticmethod
    def get_bad_txs():
        with open('bad_txs.csv', 'w+') as bad_csv:
            bad_writer = csv.writer(bad_csv)
            bad_writer.writerow(['Date', 'Block', 'From', 'To', 'Input', 'Outputs'])

            for address in TARGET_ADDRESSES:
                logger.info('looking for {} data'.format(address))
                try:
                    addr = Address.objects.get(address=address)
                except Address.DoesNotExist:
                    logger.error('{} does not exist'.format(address))
                    continue

                matched_txs = []
                for output in addr.outputs.all():
                    try:
                        if output.input.transaction in matched_txs:
                            continue

                        matched_txs.append(output.input.transaction)
                        in_values = output.input.transaction.address_inputs
                        out_values = output.input.transaction.address_outputs

                        for value_address in out_values:
                            logger.info(
                                '{} moved {} from {} to {} on {}'.format(
                                    output.input.transaction,
                                    out_values[value_address],
                                    address,
                                    value_address,
                                    output.input.transaction.time
                                )
                            )
                            bad_writer.writerow(
                                [
                                    output.input.transaction.time,
                                    output.input.transaction.block.height,
                                    address,
                                    value_address,
                                    in_values[address],
                                    out_values[value_address]
                                ]
                            )
                    except TxInput.DoesNotExist:
                        continue

    def dedupe(self):
        bad_addresses = [
            'SYguMZJM1Y3wriyU2UWzXJg25UAxBQp65y',
            'SURDRFLs8GoT16pVKcNT6igBexYqd19E6v',
            'STE9MpqdhNm7Ln9LKQQuuUFtxGhR3RvwbH',
            'SV3Jpc2yZzXVrwvy3ZSFR5FN6JEmYibQeF',
            'STyfWicxBZPu2Kn1KaoCA81e4ddYPFUPxH',
            'SN2722qP5zXbGeKrT236FtK1QsHxXBgqsH',
            'SjuvNAUH1rAoicvKZ5Tgfo2e3HAxeK42iV',
            'SdTSNATLyXZLHTbNr3L38GPfVsQZEhvxo3',
            'SkTtUJWF7G7FRSPVKbh1ATNQV3r64S7c7U',
            'SMUVkzMqYtabi2P3abFTegGZvLaUvxKRGs',
            'SgoghD15S8sKFNo13ZgHWZPVcWpeki3qLa',
            'SeVUrxMsX8N4pi79YjjEumenfPXv7FMNTw',
            'SXpG2jQsZYiczy83K6jctBBKDgZZZzDe5H',
            'ShnM5UZjSXqyBXurKXDvTL5xfbK8zBELt2',
            'ShUQd6JvN2aPY3Yv8dC593NxpT3HKDKnQr',
            'SQxrW62Sv1DZrL68kNf18u6D5H8ezq6mRN',
            'SbkCReYV5EPWxjt5PiKC5dsvEbwruvK8MC',
            'SN8qXUbj6bkZgHHktw5RtWR6YPtY6Vgdej',
            'SXfkCbPDgTJW1EAdA2WMX28N3VXTRy6j3H',
            'SfPuW3x4C2BZzUP6piWj4Y1hy9Qwn8uPSA',
            'Shm9y9t8mYbcP9yXTKGFFTfMDEepPQKDhs',
            'SirunbyyuxLGSPy2d8QNTUBv4Li7JLSC9v',
            'SUTt3nHAymXEuH6svTbvYmQT1cBEpsikwK',
            'SX6MMprHZgYd9J8euZrJMEJJFLanLQ89HE',
            'SNRVfoGSsArzC1wN81xTxn5HnCKz5xNHmG',
            'SjQSKz9twZoLZxEgMQ5ZA8GMFfG4mgD6gq'
        ]
        print([address for address in bad_addresses if address in COMPROMISED_ADDRESSES])

    def get_spent_outputs(self, address):
        spent = []
        for output in address.outputs.all():
            try:
                if output.input:
                    if output.input.transaction.index == 1:
                        continue
                    spent.append(output.input)
            except TxInput.DoesNotExist:
                pass
        return spent

    def get_transactions(self, address):
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

    def handle(self, *args, **options):
        """
        investigate the losses by tracking activity through the blockchain
        :param args:
        :param options:
        :return:
        """
        nodes = []
        edges = []

        for address in COMPROMISED_ADDRESSES:
            logger.info('working on {}'.format(address))
            # add the address to the nodes
            nodes.append({'id': address, 'label': address})
            a = Address.objects.get(address=address)
            txs = self.get_transactions(a)

            for tx in txs:
                # add the Tx to the nodes
                if not any(node['id'] == tx.tx_id for node in nodes):
                    nodes.append({'id': tx.tx_id, 'label': tx.tx_id})

                address_inputs = tx.address_inputs
                for input_address in address_inputs:
                    # for each input add an edge from the address to the tx.
                    # Add the address if it doesn't exist
                    if not any(node['id'] == input_address for node in nodes):  # noqa
                        nodes.append({
                            'id': input_address,
                            'label': input_address
                        })
                    edges.append({
                        'from': input_address,
                        'to': tx.tx_id,
                        'value': address_inputs.get(input_address, 0)/100000000
                    })

                address_outputs = tx.address_outputs
                for output_address in address_outputs:
                    # for each output add an edge from the address to the tx.
                    # Add the address if it doesn't exist
                    if not any(node['id'] == output_address for node in nodes):  # noqa
                        nodes.append({
                            'id': output_address,
                            'label': output_address
                        })
                    edges.append({
                        'from': tx.tx_id,
                        'to': output_address,
                        'value': address_outputs.get(output_address, 0) / 100000000
                    })

                    # try:
                    #     if tx_output.input:
                    #         pass
                    #         # calculate again for spending transaction
                    # except TxInput.DoesNotExist:
                    #     # unspent so add the address as a node
                    #     # if necessary and add an edge
                    #     if not any(node['id'] == tx_output.address.address for node in nodes):  # noqa
                    #         nodes.append({
                    #             'id': tx_output.address.address,
                    #             'label': tx_output.address.address
                    #         })
                    #     edges.append({
                    #         'from': tx_output.transaction.tx_id,
                    #         'to': tx_output.address.address,
                    #         'value': tx_output.value/100000000
                    #     })
            json.dump(nodes, open('nodes.json', 'w+'))
            json.dump(edges, open('edges.json', 'w+'))
            print('yup')

        print(nodes)
        print(edges)
