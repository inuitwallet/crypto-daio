import json

from django.template.loader import render_to_string

from blocks.models import Address


def get_address_details(message_dict, message):
    address = message_dict['stream']
    address_object = Address.objects.get(address=address)
    # update the balance too
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
    for tx in address_object.transactions().object_list:
        message.reply_channel.send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'address_transaction',
                        'html': render_to_string(
                            'explorer/fragments/transaction.html',
                            {
                                'tx': tx
                            }
                        )
                    }
                )
            },
            immediately=True
        )
