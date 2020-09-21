import hashlib

from tenant_schemas.test.cases import TenantTestCase
from blocks.models import Block


class TestBlock(TenantTestCase):
    def test_block_save_height_validation(self):
        height = 100
        # create a block at height 100
        Block.objects.create(height=height, hash=hashlib.sha256(b'Test Hash').hexdigest())
        # create a new block at height 100
        new_block = Block.objects.create(height=height, hash=hashlib.sha256(b'Test Hash 2').hexdigest())

        # we would expect the validation to replace the first block with new_block
        db_block = Block.objects.get(height=height)
        self.assertEqual(db_block, new_block)

    def test_block_save_height_validation_in_chain(self):
        height = 1000
        # create a bit of a chain at height
        first_block = Block.objects.create(height=height, hash=hashlib.sha256(b'In Chain 1').hexdigest())
        prev_block = Block.objects.create(height=height - 1, hash=hashlib.sha256(b'Prev Block').hexdigest())
        next_block = Block.objects.create(height=height + 1, hash=hashlib.sha256(b'Next Block').hexdigest())
        # create a new block at height
        new_block = Block.objects.create(height=height, hash=hashlib.sha256(b'In Chain 2').hexdigest())

        # we would expect the validation to replace the first block with new_block
        db_block = Block.objects.get(height=height)
        self.assertEqual(db_block, new_block)

        # also ensure block is removed from chain
        self.assertIsNone(first_block.previous_block)
        self.assertIsNone(first_block.next_block)
        self.assertIsNone(prev_block.next_block)
        self.assertIsNone(next_block.previous_block)

    def test_block_height_validation_with_self(self):
        new_block = Block.objects.create(height=101, hash=hashlib.sha256(b'Test Hash 3').hexdigest())
        altered = new_block.validate_block_height()
        # we want 'altered' to be False to show that no alteration of the block took place
        self.assertFalse(altered)

    def test_block_save_hash_validation(self):
        block_hash = hashlib.sha256(b'Same Test Hash').hexdigest()
        # create a block with hash
        first_block = Block.objects.create(height=102, hash=block_hash)
        # create a new block with same hash but different height
        second_block = Block.objects.create(height=103, hash=block_hash)

        # we would expect the validation to update the first_block with the height of the second_block
        db_block = Block.objects.get(hash=block_hash)
        self.assertEqual(db_block, first_block)
        self.assertEqual(db_block.height, second_block.height)

    def test_block_hash_validation_with_self(self):
        block_hash = hashlib.sha256(b'Same Test Hash 2').hexdigest()
        new_block = Block.objects.create(height=104, hash=block_hash)
        altered = new_block.validate_block_height()
        # we want 'altered' to be False to show that no alteration of the block took place
        self.assertFalse(altered)
