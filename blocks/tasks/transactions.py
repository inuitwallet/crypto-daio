from celery.utils.log import get_task_logger
from django.db import connection

from blocks.models import Transaction, Block, TxOutput, Address
from blocks.utils.numbers import convert_to_satoshis
from blocks.utils.rpc import get_rpc_block, get_raw_transaction
from daio.celery import app

logger = get_task_logger(__name__)


@app.task
def validate_transaction(tx_id):
    tx, _ = Transaction.objects.get_or_create(tx_id=tx_id)

    tx.validate()

    if not tx.is_valid:
        logger.warning(f"Transaction {tx} is not valid. Sending for repair")
        repair_transaction.apply(kwargs={"tx_id": tx.tx_id})
    else:
        logger.info(f"Transaction {tx} is valid")


@app.task
def parse_transaction(tx_id):
    try:
        tx = Transaction.objects.get(tx_id=tx_id)
    except Transaction.DoesNotExist:
        logger.error(f"No transaction found with tx_id {tx_id[:8]}")
        return

    rpc_tx = get_raw_transaction(tx_id, connection.schema_name)

    if not rpc_tx:
        logger.warning("No RPC Transaction returned from Daemon")
        return

    tx.parse_rpc_tx(rpc_tx)


@app.task
def repair_transaction(tx_id):
    try:
        tx = Transaction.objects.get(tx_id=tx_id)
    except Transaction.DoesNotExist:
        logger.error(f"No transaction found with tx_id {tx_id[:8]}")
        return

    # start validation and repair
    tx.validate()

    if tx.is_valid:
        logger.info(f"tx {tx} is valid")
        return

    # get the raw transaction
    rpc_tx = get_raw_transaction(tx_id, connection.schema_name)

    if not rpc_tx:
        return

    block_hash = rpc_tx.get("blockhash")

    if not block_hash:
        logger.error(f"no block hash found in rpc for tx {tx_id[:8]}")
        # indicates that block is orphaned?

        if not tx.block:
            logger.info(f"tx {tx_id[:8]} is not attached to a block")

        else:
            logger.warning(
                f"tx {tx_id[:8]} is attached to block {tx.block}. Detaching and repairing block"
            )
            app.send_task(
                "blocks.tasks.blocks.repair_block", kwargs={"block_hash": tx.block.hash}
            )
            tx.block = None
            tx.save()

        return

    # get the rpc block too for the tx_index info
    rpc_block = get_rpc_block(block_hash, connection.schema_name)

    if not rpc_block:
        logger.warning("No RPC Block returned from Daemon")
        return

    tx_id_list = [tx["txid"] for tx in rpc_block.get("tx", [])]

    if not tx_id_list:
        logger.error("problem getting tx_list from rpc_block")
        return

    tx_index = tx_id_list.index(tx_id)

    # we need the block too. block is validated at end of this task so don't worry if it was created here
    block, _ = Block.objects.get_or_create(hash=block_hash)

    logger.warning(f"tx {tx} invalid:\n{', '.join(tx.validity_errors)}")
    logger.info(f"repairing tx {tx}")

    if "incorrect index" in tx.validity_errors:
        tx.index = tx_index
        tx.save()

    if "no block" in tx.validity_errors:
        tx.block = block
        tx.save()

    if {"missing header attribute", "incorrect hash"}.intersection(
        set(tx.validity_errors)
    ):
        parse_transaction.apply(kwargs={"tx_id": tx.tx_id})
        validate_transaction.apply(kwargs={"tx_id": tx.tx_id})
        return

    if "output has no address" in tx.validity_errors:
        for tout in rpc_tx.get("vout", []):
            try:
                tx_out = tx.outputs.get(index=tout.get("n"))
            except TxOutput.DoesNotExist:
                logger.warning(f"output not found: {tout.get('n')}")
                tx.save()
                continue

            script = tout.get("scriptPubKey")

            if not script:
                logger.warning(f"no script found in tx rpc for output {tx_out}")
                continue

            if script.get("type") == "park":
                logger.info("park output")
                park_data = script.get("park", {})
                tx_out.park_duration = park_data.get("duration")
                address = park_data.get("unparkaddress")
            else:
                addresses = script.get("addresses", [])

                if not addresses:
                    logger.warning(f"no addresses found in rpc for output {tx_out}")
                    continue

                address = addresses[0]

            address_obj, _ = Address.objects.get_or_create(address=address)

            if tx_out.address == address_obj:
                logger.info(f"output {tx_out} already has address {address}")
                continue

            tx_out.address = address_obj
            # update the value too
            tx_out.value = convert_to_satoshis(tout.get("value", 0.0))
            tx_out.save()
            logger.info(f"added {address_obj.saddress} to {tx_out}")

    if {
        "address missing from previous output",
        "previous output value is 0",
        "previous output block is Missing",
        "previous output block height is None",
    }.intersection(set(tx.validity_errors)):
        fix_tx_outputs.apply(kwargs={"tx_id": tx.tx_id})

    if "park output has no duration" in tx.validity_errors:
        for tout in rpc_tx.get("vout", []):
            try:
                tx_out = tx.outputs.get(index=tout.get("n"))
            except TxOutput.DoesNotExist:
                logger.warning(f"output not found: {tout.get('n')}")
                tx.save()
                continue

            script = tout.get("scriptPubKey")

            if not script:
                logger.warning("no script found in rpc for output {}".format(tx_out))
                continue

            if script.get("type") != "park":
                continue

            park_data = script.get("park", {})
            tx_out.park_duration = park_data.get("duration")
            address = park_data.get("unparkaddress")
            address_object, _ = Address.objects.get_or_create(address=address)
            tx_out.address = address_object
            tx_out.save()
            logger.info(f"added park data to {tx_out}")

    app.send_task(
        "blocks.tasks.blocks.validate_block", kwargs={"block_hash": tx.block.hash}
    )


@app.task
def fix_tx_outputs(tx_id):
    try:
        tx = Transaction.objects.get(tx_id=tx_id)
    except Transaction.DoesNotExist:
        logger.error(f"No transaction found with tx_id {tx_id[:8]}")
        return

    scanned_transactions = []

    for tx_in in tx.inputs.all():
        if tx_in.previous_output:
            if tx_in.previous_output.transaction.block is None:
                validate_transaction.apply(
                    kwargs={"tx_id": tx_in.previous_output.transaction.tx_id}
                )
            else:
                if tx_in.previous_output.transaction.block.height is None:
                    app.send_task(
                        "blocks.tasks.blocks.validate_block",
                        kwargs={
                            "block_hash": tx_in.previous_output.transaction.block.hash
                        },
                    )

            if not tx_in.previous_output.address:
                previous_tx_id = tx_in.previous_output.transaction.tx_id

                if previous_tx_id in scanned_transactions:
                    continue

                rpc_prev_tx = get_raw_transaction(
                    previous_tx_id, connection.schema_name
                )

                for tout in rpc_prev_tx.get("vout", []):
                    if tout.get("n") != tx_in.previous_output.index:
                        continue

                    script = tout.get("scriptPubKey")

                    if not script:
                        logger.warning(
                            f"no script found in rpc for output {tx_in.previous_output}"
                        )
                        continue

                    if script.get("type") == "park":
                        logger.info("park output")
                        park_data = script.get("park", {})
                        tx_in.previous_output.park_duration = park_data.get("duration")
                        address = park_data.get("unparkaddress")
                    else:
                        addresses = script.get("addresses", [])

                        if not addresses:
                            logger.warning(
                                f"no addresses found in rpc for output {tx_in.previous_output}"
                            )
                            continue

                        address = addresses[0]

                    address_obj, _ = Address.objects.get_or_create(address=address)

                    if tx_in.previous_output.address == address_obj:
                        logger.info(
                            f"output {tx_in.previous_output} already has address {address}"
                        )
                        continue

                    tx_in.previous_output.address = address_obj
                    # update the value too
                    tx_in.previous_output.value = convert_to_satoshis(
                        tout.get("value", 0.0)
                    )
                    tx_in.previous_output.save()
                    logger.info(f"added {address} to {tx_in.previous_output}")
                    # re-validate transaction too
                    tx_in.previous_output.transaction.save()

                scanned_transactions.append(previous_tx_id)
