import hashlib
import string
from datetime import datetime
from random import randint, choice, uniform

from django.utils.timezone import make_aware
from tenant_schemas.test.cases import TenantTestCase

from blocks.models import Block, Transaction, TxOutput, Address


class TestBlock(TenantTestCase):
    def test_block_save_height_validation(self):
        height = 100
        # create a block at height 100
        Block.objects.create(
            height=height, hash=hashlib.sha256(b"Test Hash").hexdigest()
        )
        # create a new block at height 100
        new_block = Block.objects.create(
            height=height, hash=hashlib.sha256(b"Test Hash 2").hexdigest()
        )

        # we would expect the validation to replace the first block with new_block
        db_block = Block.objects.get(height=height)
        self.assertEqual(db_block, new_block)

    def test_block_save_height_validation_in_chain(self):
        height = 1000
        # create a bit of a chain at height
        first_block = Block.objects.create(
            height=height, hash=hashlib.sha256(b"In Chain 1").hexdigest()
        )
        prev_block = Block.objects.create(
            height=height - 1, hash=hashlib.sha256(b"Prev Block").hexdigest()
        )
        next_block = Block.objects.create(
            height=height + 1, hash=hashlib.sha256(b"Next Block").hexdigest()
        )
        # create a new block at height
        new_block = Block.objects.create(
            height=height, hash=hashlib.sha256(b"In Chain 2").hexdigest()
        )

        # we would expect the validation to replace the first block with new_block
        db_block = Block.objects.get(height=height)
        self.assertEqual(db_block, new_block)

        # also ensure block is removed from chain
        self.assertIsNone(first_block.previous_block)
        self.assertIsNone(first_block.next_block)
        self.assertIsNone(prev_block.next_block)
        self.assertIsNone(next_block.previous_block)

    def test_block_height_validation_with_self(self):
        new_block = Block.objects.create(
            height=101, hash=hashlib.sha256(b"Test Hash 3").hexdigest()
        )
        altered = new_block.validate_block_height()
        # we want 'altered' to be False to show that no alteration of the block took place
        self.assertFalse(altered)

    def test_block_save_hash_validation(self):
        block_hash = hashlib.sha256(b"Same Test Hash").hexdigest()
        # create a block with hash
        first_block = Block.objects.create(height=102, hash=block_hash)
        # create a new block with same hash but different height
        second_block = Block.objects.create(height=103, hash=block_hash)

        # we would expect the validation to update the first_block with the height of the second_block
        db_block = Block.objects.get(hash=block_hash)
        self.assertEqual(db_block, first_block)
        self.assertEqual(db_block.height, second_block.height)

    def test_block_hash_validation_with_self(self):
        block_hash = hashlib.sha256(b"Same Test Hash 2").hexdigest()
        new_block = Block.objects.create(height=104, hash=block_hash)
        altered = new_block.validate_block_height()
        # we want 'altered' to be False to show that no alteration of the block took place
        self.assertFalse(altered)

    def test_serialize(self):
        # create block parameters
        height = randint(1000, 2000)
        hash = hashlib.sha256(b"Serialize Block").hexdigest()
        size = randint(1, 5000)
        version = randint(1, 1000)
        merkleroot = hashlib.sha256(b"Merkle").hexdigest()
        time = make_aware(datetime(randint(2014, 2020), randint(1, 12), randint(1, 28)))
        nonce = randint(1, 4)
        bits = "".join(choice(string.hexdigits) for _ in range(10))
        difficulty = uniform(1, 500)
        mint = uniform(1, 500)
        previous_block = Block.objects.create(
            height=height - 1, hash=hashlib.sha256(b"Previous Block").hexdigest()
        )
        next_block = Block.objects.create(
            height=height + 1, hash=hashlib.sha256(b"Next Block").hexdigest()
        )
        flags = "".join(choice(string.hexdigits) for _ in range(randint(100, 610)))
        proof_hash = "".join(choice(string.hexdigits) for _ in range(randint(100, 610)))
        entropy_bit = randint(1, 1000)
        modifier = "".join(choice(string.hexdigits) for _ in range(randint(100, 610)))
        modifier_checksum = "".join(
            choice(string.hexdigits) for _ in range(randint(100, 610))
        )
        coinage_destroyed = randint(1, 5000)

        # create the block
        block = Block.objects.create(
            height=height,
            hash=hash,
            size=size,
            version=version,
            merkle_root=merkleroot,
            time=time,
            nonce=nonce,
            bits=bits,
            difficulty=difficulty,
            mint=mint,
            flags=flags,
            proof_hash=proof_hash,
            entropy_bit=entropy_bit,
            modifier=modifier,
            modifier_checksum=modifier_checksum,
            coinage_destroyed=coinage_destroyed,
            previous_block=previous_block,
            next_block=next_block,
        )
        # create two basic transaction
        Transaction.objects.create(
            tx_id=hashlib.sha256(b"Tx0").hexdigest(), block=block, index=0
        )
        tx1 = Transaction.objects.create(
            tx_id=hashlib.sha256(b"Tx1").hexdigest(), block=block, index=1
        )
        # create an output for tx 1 at index 1 with an address output
        address = "".join(choice(string.hexdigits) for _ in range(28))
        TxOutput.objects.create(
            transaction=tx1, index=1, address=Address.objects.create(address=address)
        )

        serialized_block = block.serialize()
        expected = {
            "hash": hash,
            "height": height,
            "size": size,
            "version": version,
            "merkleroot": merkleroot,
            "time": datetime.strftime(time, "%Y-%m-%d %H:%M:%S %Z"),
            "nonce": nonce,
            "bits": bits,
            "difficulty": difficulty,
            "mint": mint,
            "flags": flags,
            "proofhash": proof_hash,
            "entropybit": entropy_bit,
            "modifier": modifier,
            "modifierchecksum": modifier_checksum,
            "coinagedestroyed": coinage_destroyed,
            "previousblockhash": previous_block.hash,
            "nextblockhash": next_block.hash,
            "valid": False,
            "number_of_transactions": 2,
            "solved_by": address,
        }

        self.assertEqual(serialized_block, expected)
