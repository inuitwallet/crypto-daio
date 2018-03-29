import json

from django.db.models import Sum, Min
from django.template.loader import render_to_string

from blocks.models import Block, TxOutput, CustodianVote


def send_transactions(block, message):
    # send the block transactions
    transactions = block.transactions.all()

    if transactions.count() > 0:
        message.reply_channel.send(
            {'text': json.dumps({'message_type': 'has_transactions'})},
            immediately=True
        )

    for tx in transactions:
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


def send_custodial_grant_votes(block, message):
    # send the block custodial grants
    custodian_votes = block.custodianvote_set.all()

    if custodian_votes.count() > 0:
        message.reply_channel.send(
            {'text': json.dumps({'message_type': 'has_grants'})},
            immediately=True
        )

    for grant in custodian_votes:
        granted = None
        for grant_output in TxOutput.objects.filter(
            address=grant.address,
            value=grant.amount * 10000,
        ):
            if not grant_output.transaction.block:
                continue

            for tx_input in grant_output.transaction.inputs.all():
                if not tx_input.previous_output:
                    granted = tx_input.transaction.block

        message.reply_channel.send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'block_grant',
                        'html': render_to_string(
                            'explorer/fragments/block_grant.html',
                            {
                                'grant': {
                                    'address': grant.address.address,
                                    'amount': grant.amount,
                                    'granted': granted
                                }
                            }
                        )
                    }
                )
            },
            immediately=True
        )


def send_motion_votes(block, message):
    motion_votes = block.motionvote_set.all()

    if motion_votes.count() > 0:
        message.reply_channel.send(
            {'text': json.dumps({'message_type': 'has_motions'})},
            immediately=True
        )

    for motion in motion_votes:
        message.reply_channel.send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'block_motion',
                        'html': render_to_string(
                            'explorer/fragments/block_motion.html',
                            {
                                'motion': {
                                    'hash': motion.hash,
                                }
                            }
                        )
                    }
                )
            },
            immediately=True
        )


def send_park_rate_votes(block, message):
    park_rate_votes = block.parkratevote_set.all().order_by('coin__index')

    if park_rate_votes.count() > 0:
        message.reply_channel.send(
            {'text': json.dumps({'message_type': 'has_park_rates'})},
            immediately=True
        )

    for park_rate_vote in park_rate_votes:
        message.reply_channel.send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'block_park_rate',
                        'html': render_to_string(
                            'explorer/fragments/block_park_rate.html',
                            {
                                'park_rate': park_rate_vote,

                            }
                        )
                    }
                )
            },
            immediately=True
        )


def send_fees_votes(block, message):
    fees_votes = block.feesvote_set.all().order_by('coin__index')

    if fees_votes.count() > 0:
        message.reply_channel.send(
            {'text': json.dumps({'message_type': 'has_fees'})},
            immediately=True
        )

    for fees in fees_votes:
        message.reply_channel.send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'block_fees',
                        'html': render_to_string(
                            'explorer/fragments/block_fees.html',
                            {
                                'fees': fees
                            }
                        )
                    }
                )
            },
            immediately=True
        )


def get_block_details(message_dict, message):
    block_hash = message_dict['stream']

    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        return

    # clear the existing details
    message.reply_channel.send(
        {'text': json.dumps({'message_type': 'clear_block_details'})},
        immediately=True
    )

    send_transactions(block, message)
    send_custodial_grant_votes(block, message)
    send_motion_votes(block, message)
    send_park_rate_votes(block, message)
    send_fees_votes(block, message)
