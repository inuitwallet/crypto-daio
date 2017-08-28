import json
import logging

from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def get_address_balance(address_object, message):
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'address_balance',
                    'balance': address_object.balance
                }
            )
        },
        immediately=True
    )


def get_address_details(address_object, message):
    for tx in address_object.transactions().object_list:
        message.reply_channel.send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'address_transaction',
                        'html': render_to_string(
                            'explorer/fragments/address_transaction.html',
                            {'tx': tx}
                        )
                    }
                )
            }
        )
