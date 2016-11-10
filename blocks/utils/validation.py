import hashlib
import struct
import time


def calc_block_hash(block):
    header = (
        struct.pack('<L', block.version) +
        block.previous_block.hash.decode('hex')[::-1] +
        block.merkle_root.decode('hex')[::-1] +
        struct.pack('<L', int(time.mktime(block.time.timetuple()))) +
        block.bits.decode('hex')[::-1] +
        struct.pack('<L', block.nonce)
    )
    hash = hashlib.sha256(hashlib.sha256(header).digest()).digest()
    hash.encode('hex_codec')
    return hash[::-1].encode('hex_codec')


def calc_tx_hash(tx):
    tx_inputs = ''
    for tx_input in tx.inputs.all():
        tx_inputs += (
            tx_input.tx_id.decode('hex')[::-1]
            if tx_input.tx_id is not None
            else ''
        )
        tx_inputs += struct.pack('<L', tx_input.v_out)
        tx_inputs += (
            tx_input.coin_base.decode('hex')[::-1]
            if tx_input.coin_base is not None
            else ''
        )
        tx_inputs += struct.pack('<L', tx_input.sequence)

    header = (
        struct.pack('<L', tx.version) +
        struct.pack('<I', tx.inputs.all().count()) +
        tx_inputs
    )
    print(header.encode('hex'))


if __name__ == '__main__':
    import django
    django.setup()
    from blocks.models import Block
    for block in Block.objects.all().order_by('height'):
        try:
            calc_hash = calc_block_hash(block)
        except (AttributeError, struct.error) as e:
            print('problem with block {}: {}'.format(block.height, e.message))
            calc_hash = None
            continue

        if calc_hash != block.hash:
            print('hashes for block {} do not match'.format(block.height))
            continue

        for tx in block.transactions.all():
            try:
                calc_tx_hash(tx)
            except AttributeError as e:
                print(
                    'problem with tx {} on block {}: {}'.format(
                        tx.tx_id,
                        block.height,
                        e.message
                    )
                )
