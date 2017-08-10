import json

from django.template.loader import render_to_string

from blocks.models import Block


def get_block_transactions(message_dict, message):
    block_hash = message_dict['stream']
    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        return
    for tx in block.transactions.all():
        message.reply_channel.send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'block_transaction',
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
