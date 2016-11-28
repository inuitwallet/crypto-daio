import hashlib
import struct
import time
from threading import Thread


def calc_block_hash(block):
    header = (
        struct.pack('<L', block.version) +
        block.previous_block.hash.decode('hex')[::-1] +
        block.merkle_root.decode('hex')[::-1] +
        struct.pack('<L', int(time.mktime(block.time.timetuple()))) +
        block.bits.decode('hex')[::-1] +
        struct.pack('<L', block.nonce)
    )
    header_hash = hashlib.sha256(hashlib.sha256(header).digest()).digest()
    header_hash.encode('hex_codec')
    return header_hash[::-1].encode('hex_codec')


def calc_tx_hash(tx):
    tx_inputs = ''
    for tx_input in tx.inputs.all():
        # previous output transaction hash
        tx_inputs += (
            tx_input.output_transaction.tx_id.decode('hex')[::-1]
            if tx_input.output_transaction is not None
            else ('0'*64).decode('hex')[::-1]
        )
        # previous output N
        tx_inputs += (
            struct.pack('<L', tx_input.v_out)
            if tx_input.v_out is not None
            else 'ffffffff'.decode('hex')[::-1]
        )
        script = (
            tx_input.output_transaction.decode('hex')[::-1]
            if tx_input.coin_base is not None
            else ''
        )
        tx_inputs += struct.pack('<I', len(script))
        tx_inputs += script
        tx_inputs += struct.pack('<L', tx_input.sequence)

    tx_outputs = ''
    for tx_output in tx.outputs.all():
        tx_outputs += (
            struct.pack('L', tx_output.value) +
            tx_output.script_pub_key_hex.decode('hex')[::-1]
        )

    header = (
        struct.pack('<L', tx.version) +
        struct.pack('<I', tx.inputs.all().count()) +
        tx_inputs +
        struct.pack('<I', tx.outputs.all().count()) +
        tx_outputs +
        struct.pack('<L', tx.lock_time)
    )
    print(struct.pack('<I', tx.inputs.all().count()).encode('hex_codec'))
    header_hash = hashlib.sha256(hashlib.sha256(header).digest()).digest()
    header_hash.encode('hex_codec')
    return header_hash[::-1].encode('hex_codec')


if __name__ == '__main__':
    import django
    django.setup()
    from blocks.models import Block
    from blocks.utils.block_parser import save_block
    from blocks.utils.rpc import send_rpc

    try:
        latest_block_id = Block.objects.latest('id').id
    except Block.DoesNotExist:
        latest_block_id = 0

    for i in range(latest_block_id):
        try:
            block = Block.objects.get(id=i)
        except Block.DoesNotExist:
            print('no block with id {}'.format(i))
            continue
        try:
            calc_hash = calc_block_hash(block)
        except (AttributeError, struct.error) as e:
            print('problem with block {}: {}'.format(block.height, e.message))
            calc_hash = None

        if calc_hash != block.hash:
            print('hashes for block {} do not match'.format(block.height))
            print('{}\n{}'.format(block.hash, calc_hash))
            rpc = send_rpc(
                {
                    'method': 'getblock',
                    'params': [block.hash]
                }
            )
            got_block = rpc['result'] if not rpc['error'] else None
            if got_block:
                save = Thread(
                    target=save_block,
                    kwargs={
                        'block': got_block,
                    },
                    name=block.hash
                )
                save.daemon = True
                save.start()

        #for tx in block.transactions.all():
        #    try:
        #        calc_tx_hash = calc_tx_hash(tx)
        #    except AttributeError as e:
        #        print(
        #            'problem with tx {} on block {}: {}'.format(
        #                tx.tx_id,
        #                block.height,
        #                e.message
        #            )
        #       )
        #    print(calc_tx_hash)
        #    print(tx.tx_id)
        #    assert calc_tx_hash == tx.tx_id

