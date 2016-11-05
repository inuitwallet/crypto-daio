from blocks.models import Block


def main():
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

if __name__ == '__main__':
    main()
