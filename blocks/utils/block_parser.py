import json
from threading import Thread, enumerate
import time
from datetime import datetime as dt

import requests
from blocks.models import Block, Transaction, TxInput, TxOutput, Address, WatchAddress
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils import timezone
from rpc import send_rpc
import logging

logger = logging.getLogger('block_parser')

tz = timezone.get_current_timezone()


def save_block(block):
    """
    :param block:
    :return:
    """
    # Try and get the bloch hash from the passed block
    try:
        block_hash = block.get('hash', None)
    except AttributeError as e:
        logger.error('parse error {}'.format(e))
        return
    # get or create the block
    this_block, _ = Block.objects.get_or_create(hash=block_hash)
    logger.info('parsing {}'.format(block_hash))
    this_block.size = block.get('size', None)
    this_block.height = block.get('height', None)
    this_block.version = block.get('version', None)
    this_block.merkle_root = block.get('merkleroot', None)
    this_block.time = tz.localize(
        dt.strptime(
            block.get('time', None),
            '%Y-%m-%d %H:%M:%S %Z'
        )
    )
    this_block.nonce = block.get('nonce', None)
    this_block.bits = block.get('bits', None)
    this_block.difficulty = block.get('difficulty', None)
    this_block.mint = block.get('mint', None)
    this_block.previous_block_hash = block.get('previousblockhash', None)
    this_block.next_block_hash = block.get('nextblockhash', None)
    this_block.flags = block.get('flags', None)
    this_block.proof_hash = block.get('proofhash', None)
    this_block.entropy_bit = block.get('entropybit', None)
    this_block.modifier = block.get('modifier', None)
    this_block.modifier_checksum = block.get('modifierchecksum', None)
    this_block.coinage_destroyed = block.get('coinagedestroyed', None)

    this_block.save()

    # for each transaction in the block, save a new transaction
    for tx in block.get('tx', []):
        transaction = Transaction.objects.create(
            block=this_block,
            tx_id=tx.get('txid', None),
            version=tx.get('version', None),
            lock_time=tx.get('locktime', None),
            is_coin_base=tx.get('is_coinbase', None),
            is_coin_stake=tx.get('is_coinstake', None),
        )
        # for each input in the transaction, save a TxInput
        for vin in tx.get('vin', []):
            tx_input = TxInput.objects.create(
                transaction=transaction,
                tx_id=vin.get('txid', None),
                v_out=vin.get('vout', None),
                sequence=vin.get('sequence', None),
                coin_base=vin.get('coinbase', None),
            )
        # similar for each TxOutput
        for vout in tx.get('vout', []):
            script_pubkey = vout.get('scriptPubKey', {})
            tx_output = TxOutput.objects.create(
                transaction=transaction,
                value=vout.get('value', 0),
                n=vout.get('n', None),
                script_pub_key_asm=script_pubkey.get('asm', None),
                script_pub_key_hex=script_pubkey.get('hex', None),
                script_pub_key_type=script_pubkey.get('type', None),
                script_pub_key_req_sig=script_pubkey.get('reqSig', None),
            )
            # save each address in the output
            for addr in script_pubkey.get('addresses', []):
                address, created = Address.objects.get_or_create(
                    address=addr,
                )
                if created:
                    # TODO Calculate address balance to this point in the blockchain
                    # TODO and save it along side address.
                    address.save()
                tx_output.addresses.add(address)
                tx_output.save()
                # check the address against the list of addresses to watch
                check_thread = Thread(
                    target=check_watch_addresses,
                    kwargs={
                        'address': address[0],
                        'value': tx_output[0].value,
                    }
                )
                check_thread.daemon = True
                check_thread.start()
    logger.info('saved block {}'.format(this_block.height))
    return


def check_watch_addresses(address, value):
    """
    We check the list of watched addresses and reduce the expected amount by the value
    :param address:
    :param value:
    :return:
    """
    # we work with unique addresses so get() should be safe here
    try:
        watched_address = WatchAddress.objects.get(address=address)
    except (MultipleObjectsReturned, ObjectDoesNotExist):
        return
    # we have a watched address. lets reduce the value
    watched_address.amount -= float(value)
    watched_address.save()
    if watched_address.amount <= 0.0:
        response = requests.post(
            url=watched_address.call_back,
            headers={'Content-Type': 'application/json'},
            data=json.loads(
                {
                    'address': address,
                }
            )
        )
    return


def start_parse():
    # Get current height from Coin Daemon
    rpc = send_rpc(
        {
            'method': 'getblockcount',
        }
    )
    daemon_height = rpc['result'] if not rpc['error'] else 0

    db_height = settings.LAST_GOOD_BLOCK
    logger.info('parsing blockchain from {} to {}'.format(db_height, daemon_height))
    time.sleep(3)
    while db_height < daemon_height:
        # see if the block exists
        try:
            Block.objects.get(height=db_height)
        except ObjectDoesNotExist:
            # get the block hash
            rpc = send_rpc(
                {
                    'method': 'getblockhash',
                    'params': [db_height]
                }
            )
            got_block_hash = rpc['result'] if not rpc['error'] else None
            # get the block data
            rpc = send_rpc(
                {
                    'method': 'getblock',
                    'params': [got_block_hash, True, True]
                }
            )
            got_block = rpc['result'] if not rpc['error'] else None
            if got_block:
                save = Thread(
                    target=save_block,
                    kwargs={
                        'block': got_block,
                    },
                    name=got_block_hash
                )
                if got_block_hash not in enumerate():
                    save.daemon = True
                    save.start()
                    time.sleep(0.2)
        logger.info('checked block {}'.format(db_height))
        db_height += 1

