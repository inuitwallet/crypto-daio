from celery.utils.log import get_task_logger
from django.db import connection

from blocks.models import Block, Transaction
from blocks.utils.rpc import get_block_hash, get_rpc_block, send_rpc
from daio.celery import app

logger = get_task_logger(__name__)


@app.task
def get_block(height):
    """
    Get the block from the rpc connection at the given height
    Ensure that if a different block exists at this height, its height is set to None
    """
    logger.info(f"Getting block {height}")
    block_hash = get_block_hash(height, connection.schema_name)

    if not block_hash:
        logger.warning("No block hash returned from daemon")
        return

    db_hash_block, _ = Block.objects.get_or_create(hash=block_hash)

    try:
        db_height_block = Block.objects.get(height=height)
    except Block.DoesNotExist:
        db_height_block = db_hash_block

    if db_hash_block != db_height_block:
        db_height_block.height = None
        db_height_block.save()

    rpc_block = get_rpc_block(db_hash_block.hash, connection.schema_name)

    if not rpc_block:
        logger.warning("No RPC Block returned from Daemon")
        return

    db_hash_block.parse_rpc_block(rpc_block)
    db_hash_block.validate()

    if not db_hash_block.is_valid:
        logger.warning(f"Block {db_hash_block} is not valid. Sending for repair")
        repair_block.delay(db_hash_block.hash)

    return


@app.task
def repair_block(block_hash):
    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error(f"No block found with hash {block_hash}")
        return

    block.validate()

    if block.is_valid:
        logger.info(f"block {block} is valid")
        return

    logger.info(f"repairing block {block}:\n{', '.join(block.validity_errors)}")

    # merkle root error means missing, extra or duplicate transactions
    if {"merkle root incorrect", "incorrect tx indexing"}.intersection(
        set(block.validity_errors)
    ):
        fix_merkle_root.delay(block.hash)

    if {
        "missing attribute: self.previous_block",
        "no previous block hash",
        "incorrect previous height",
        "no previous block hash",
    }.intersection(set(block.validity_errors)):
        fix_adjoining_block.delay(block.hash, -1)

    if {
        "incorrect next height",
        "next block does not lead on from this block",
        "missing next block",
    }.intersection(set(block.validity_errors)):
        fix_adjoining_block.delay(block.hash, 1)

    if {
        "custodian votes do not match",
        "park rate votes do not match",
        "motion votes do not match",
        "fee votes do not match",
    }.intersection(set(block.validity_errors)):
        fix_block_votes.delay(block.hash)

    if "active park rates do not match" in block.validity_errors:
        fix_block_park_rates.delay(block.hash)

    # all other errors with the block can be solved by re-parsing it
    logger.info("re-parsing {}".format(block))
    rpc_block = get_rpc_block(block.hash, connection.schema_name)

    if not rpc_block:
        logger.warning("No RPC Block returned from Daemon")
        return

    block.parse_rpc_block(rpc_block)


@app.task
def fix_merkle_root(block_hash):
    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error(f"No block found with hash {block_hash}")
        return

    logger.info(f"fixing merkle root on block {block}")

    rpc, msg = send_rpc(
        {"method": "getblock", "params": [block.hash],},
        schema_name=connection.schema_name,
    )

    if not rpc:
        return False

    transactions = rpc.get("tx", [])
    block_tx = block.transactions.all().values_list("tx_id", flat=True)

    # add missing transactions
    for tx_id in list(set(transactions) - set(block_tx)):
        logger.info(f"adding missing tx {tx_id[:8]} to {block}")
        tx, _ = Transaction.objects.get_or_create(tx_id=tx_id)
        tx.block = block
        tx.save()

    # remove additional transactions
    for tx in block.transactions.all():
        if tx.tx_id not in transactions:
            logger.error(f"tx {tx} does not belong to block {block}")
            tx.delete()
            continue

        # fix index
        rpc_index = transactions.index(tx.tx_id)

        if tx.index != rpc_index:
            logger.error(f"incorrect index for tx {tx}: ({rpc_index})")
            tx.index = rpc_index

        tx.save()

    block.save()


@app.task
def fix_adjoining_block(block_hash, height_diff):
    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error(f"No block found with hash {block_hash}")
        return

    logger.info("fixing adjoining block for {}".format(block))
    adjoining_hash = get_block_hash(
        block.height + height_diff, schema_name=connection.schema_name
    )

    if not adjoining_hash:
        return

    adjoining_hash_block, _ = Block.objects.get_or_create(hash=adjoining_hash)

    try:
        adjoining_height_block = Block.objects.get(height=block.height + height_diff)
    except Block.DoesNotExist:
        adjoining_height_block = adjoining_hash_block

    if adjoining_hash_block != adjoining_height_block:
        # the block with the previous height doesn't match the hash from this block
        # likely to be an orphan so remove it
        adjoining_height_block.height = None
        adjoining_height_block.save()

    if height_diff == -1:
        block.previous_block = adjoining_hash_block
        adjoining_hash_block.next_block = block
    else:
        block.next_block = adjoining_hash_block
        adjoining_hash_block.previous_block = block

    block.save()

    adjoining_hash_block.height = block.height + height_diff
    adjoining_hash_block.save()

    adjoining_hash_block.validate()

    if not adjoining_hash_block.is_valid:
        logger.warning(f"Block {adjoining_hash_block} is not valid. Sending for repair")
        repair_block.delay(adjoining_hash_block.hash)


@app.task
def fix_block_votes(block_hash):
    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error(f"No block found with hash {block_hash}")
        return

    logger.info(f"fixing votes on block {block}")

    rpc, msg = send_rpc(
        {"method": "getblock", "params": [block.hash],},
        schema_name=connection.schema_name,
    )

    if not rpc:
        return False

    vote = rpc.get("vote", {})
    block.parse_rpc_votes(vote)
    block.vote = vote
    block.save()


@app.task
def fix_block_park_rates(block_hash):
    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error(f"No block found with hash {block_hash}")
        return

    logger.info(f"fixing park rates on block {block}")
    rpc, msg = send_rpc(
        {"method": "getblock", "params": [block.hash],},
        schema_name=connection.schema_name,
    )

    if not rpc:
        return False

    park_rates = rpc.get("parkrates", [])
    block.parse_rpc_parkrates(park_rates)
    block.park_rates = park_rates
    block.save()
