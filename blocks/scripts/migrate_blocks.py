import django
django.setup()

from blocks.models import Block, TxInput, Transaction


def migrate_blocks():
    for block in Block.objects.all():
        print('migrating block {}'.format(block.height))
        try:
            block.previous_block = Block.objects.get(hash=block.previous_block_hash)
        except Block.DoesNotExist:
            pass

        try:
            block.next_block = Block.objects.get(hash=block.next_block_hash)
        except Block.DoesNotExist:
            pass

        block.save()


def migrate_tx_inputs():
    for tx_input in TxInput.objects.all():
        print('migrating txinput {}'.format(tx_input))
        try:
            tx_input.output_transaction = Transaction.objects.get(tx_id=tx_input.tx_id)
        except Transaction.DoesNotExist:
            pass

        tx_input.save()

if __name__ == '__main__':
    #migrate_blocks()
    migrate_tx_inputs()
