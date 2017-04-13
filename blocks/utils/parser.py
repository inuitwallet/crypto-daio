from datetime import datetime
from logging.handlers import RotatingFileHandler
from threading import Thread

import logging

from django.utils.timezone import make_aware
from django.db import IntegrityError

from blocks.models import Block
from blocks.utils.rpc import send_rpc


logger = logging.getLogger('block_parser')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)

rf = RotatingFileHandler('parse.log', maxBytes=4194304, backupCount=5)
rf.setLevel(logging.DEBUG)
rf.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(rf)


def save_block(block):
    """
    Parse and save a Block object.
    """
    # Try and get the block hash from the passed block
    try:
        block_hash = block.get('hash', None)
    except AttributeError as e:
        logger.error('rpc block has no hash {}: {}'.format(block, e))
        return
    # get or create the block
    this_block, _ = Block.objects.get_or_create(hash=block_hash)
    # get the height and log the block
    this_block.height = block.get('height', None)
    logger.info('parsing {} at height {}'.format(block_hash, this_block.height))
    # parse the json and apply to the block we just fetched
    this_block.size = block.get('size', None)
    this_block.version = block.get('version', None)
    this_block.merkle_root = block.get('merkleroot', None)
    this_block.time = make_aware(
        datetime.strptime(
            block.get('time', None),
            '%Y-%m-%d %H:%M:%S %Z'
        )
    )
    this_block.nonce = block.get('nonce', None)
    this_block.bits = block.get('bits', None)
    this_block.difficulty = block.get('difficulty', None)
    this_block.mint = block.get('mint', None)
    this_block.flags = block.get('flags', None)
    this_block.proof_hash = block.get('proofhash', None)
    this_block.entropy_bit = block.get('entropybit', None)
    this_block.modifier = block.get('modifier', None)
    this_block.modifier_checksum = block.get('modifierchecksum', None)
    this_block.coinage_destroyed = block.get('coinagedestroyed', None)

    # using the previousblockhash, get the block object to connect
    prev_block_hash = block.get('previousblockhash', None)
    try:

        previous_block = Block.objects.get(
            hash=prev_block_hash
        )
        this_block.previous_block = previous_block
        # update the previous block with this block as its next block
        previous_block.next_block = this_block
        previous_block.save()
    except Block.DoesNotExist:
        logger.warning('Previous Block {} Does not exist'.format(prev_block_hash))
        # if the previous block should exist we create it to link it to this block
        # and then trigger a parse of that block
        if prev_block_hash is not None:
            previous_block = Block.objects.create(
                hash=prev_block_hash,
                next_block=this_block,
            )
            previous_block.save()
            trigger_block_parse(prev_block_hash)

    # do the same for the next block
    next_block_hash = block.get('nextblockhash', None)
    try:
        next_block = Block.objects.get(
            hash=next_block_hash
        )
        this_block.next_block = next_block
    except Block.DoesNotExist:
        logger.warning('Next Block {} Does not exist'.format(next_block_hash))
        # if the next block should exist we create it to link it to this block
        # and then trigger a parse of that block
        if next_block_hash is not None:
            next_block = Block.objects.create(
                hash=next_block_hash,
            )
            next_block.save()
            this_block.next_block = next_block
            trigger_block_parse(next_block.hash)

    # attempt to save this block. Orphan blocks can appear which ruins data integrity
    # if we find a previous block with the same height already exists we check the
    # hashes of both. If they differ we prefer the newer block as we can assume
    # it has come directly from, the coin daemon.
    try:
        this_block.save()
        logger.info('saved block {}'.format(this_block.height))
    except IntegrityError:
        logger.info('block {} already exists'.format(this_block.height))
        existing_block = Block.objects.get(height=this_block.height)
        if existing_block.hash != this_block.hash:
            for transaction in existing_block.transactions.all():
                for tx_input in transaction.inputs.all():
                    tx_input.delete()
                for tx_output in transaction.outputs.all():
                    tx_output.delete()
                transaction.delete()
            existing_block.delete()
            this_block.save()
            logger.info('saved new block {}'.format(this_block.height))
        else:
            logger.info(
                'hashes match. leaving existing block {}'.format(existing_block.height)
            )

    # ow get the transaction hashes and request their data from the daemon
    for tx_hash in block.get('tx', []):
        logger.info('scanning tx {}'.format(tx_hash))
        trigger_transaction_parse(this_block, tx_hash)


def trigger_block_parse(block_hash, blocking=False):
    """
    For the given block hash, request the block json from the coin daemon and
    trigger the save method. specify blocking=True to call the save method directly
    otherwise it is called in a new thread
    """
    rpc = send_rpc(
        {
            'method': 'getblock',
            'params': [block_hash]
        }
    )
    got_block = rpc['result'] if not rpc['error'] else None
    if got_block:
        if blocking:
            save_block(block=got_block)
        else:
            save = Thread(
                target=save_block,
                kwargs={
                    'block': got_block,
                },
                name=block_hash
            )
            save.daemon = True
            save.start()
