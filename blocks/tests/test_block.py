import hashlib
import string
from datetime import datetime
from random import randint, choice, uniform

from django.utils.timezone import make_aware
from tenant_schemas.test.cases import TenantTestCase

from blocks.models import Block, Transaction, TxOutput, Address


class TestBlock(TenantTestCase):
    def test_serialize(self):
        # create block parameters
        height = randint(1500, 2000)
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

    def test_validate(self):
        height = 1000
        block_hash = hashlib.sha256(b"Validate Block").hexdigest()

        block = Block.objects.create(height=height, hash=block_hash)
        block.validate()

        self.assertFalse(block.is_valid)
        self.assertEqual(
            set(block.validity_errors),
            {"merkle root incorrect", "missing header attribute", "no previous block"},
        )

        previous_block = Block.objects.create(
            height=height - 1,
            hash=hashlib.sha256(b"Previous Validate Block").hexdigest(),
        )
        block.previous_block = previous_block
        block.version = 1
        block.merkle_root = (
            "d11c7d89ab966802bbd4d738ffffae2aa7e8486a166f31a93f02cd10d77d3b8d"
        )
        block.time = make_aware(datetime(2018, 1, 1))
        block.bits = "1e0fffff"
        block.nonce = 0
        block.save()
        block.validate()

        self.assertFalse(block.is_valid)
        self.assertEqual(
            set(block.validity_errors),
            {
                "previous block does not point to this block",
                "merkle root incorrect",
                "previous block has no previous block",
                "incorrect block hash",
            },
        )

        previous_block.previous_block = Block.objects.create(
            height=height - 2,
            hash=hashlib.sha256(b"Previous Previous Validate Block").hexdigest(),
        )
        previous_block.next_block = block
        previous_block.save()

        block.validate()
        self.assertFalse(block.is_valid)
        self.assertEqual(
            set(block.validity_errors),
            {"merkle root incorrect", "incorrect block hash"},
        )

        tx_1 = Transaction.objects.create(
            block=block,
            tx_id="e6f089cda1edf1d767f1a4803ca121bdf633e018b43eef12c9d634e7b2999434",
        )
        tx_2 = Transaction.objects.create(
            block=block,
            tx_id="badd47983f391b83f97ba33a6ce918592d8545d3747e247f226a14f0eab69e0f",
        )

        block.validate()
        self.assertFalse(block.is_valid)
        self.assertEqual(
            set(block.validity_errors),
            {"incorrect block hash", "incorrect tx indexing"},
        )

        tx_1.index = 0
        tx_1.save()
        tx_2.index = 1
        tx_2.save()

        block.validate()
        self.assertFalse(block.is_valid)
        self.assertEqual(set(block.validity_errors), {"incorrect block hash"})

        block.hash = "b7d80252fb4c16f641383fad06a4e325491d7e88b5c4d8e68465f53bf167c5d5"
        block.save()
        previous_block.hash = (
            "f8290bbd3bc06b3d5c67a79ee5a0fa7fe22c749ed2bf3a1312cf910bcfd39bd0"
        )
        previous_block.save()

        block.validate()
        self.assertTrue(block.is_valid)
