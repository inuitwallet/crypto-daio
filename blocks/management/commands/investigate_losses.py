import csv
import json
import logging

from django.core.management import BaseCommand
from django.utils import timezone

from blocks.models import Address, TxInput

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()



class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        investigate the losses by tracking activity through the blockchain
        :param args:
        :param options:
        :return:
        """
        compromised_addresses = [
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

        target_addresses = [
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

        with open('losses.csv', 'w+') as losses_file:
            loss_writer = csv.writer(losses_file)
            loss_writer.writerow(['From', 'To', 'Date', 'Block', 'Input', 'Outputs'])

            for address in compromised_addresses:
                logger.info('looking for {} data'.format(address))
                try:
                    addr = Address.objects.get(address=address)
                except Address.DoesNotExist:
                    logger.error('{} does not exist'.format(address))
                    continue

                for start_output in addr.outputs.all().order_by(
                    'transaction__block__height'
                ):
                    try:
                        for output in start_output.input.transaction.outputs.all():
                            if not output.address:
                                output.transaction.block.save()
                                continue
                            if output.address.address in target_addresses:
                                values = output.transaction.address_outputs
                                logger.info(
                                    'transaction {} moved funds from {} to {} on {}: '
                                    '{}'.format(
                                        output.transaction,
                                        address,
                                        output.address.address,
                                        output.transaction.time,
                                        values
                                    )
                                )
                                loss_writer.writerow(
                                    [
                                        address,
                                        output.address.address,
                                        output.transaction.time,
                                        output.transaction.block.height,
                                        start_output.value,
                                        values
                                    ]
                                )
                                break
                    except TxInput.DoesNotExist:
                        continue
