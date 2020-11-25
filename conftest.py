import hashlib
import string
from datetime import datetime
from random import randint, choice, uniform

import pytest
from django.utils.timezone import make_aware

from blocks.models import Block

pytest_plugins = ["helpers_namespace"]


@pytest.helpers.register
def generate_block(block_hash):
    # create block parameters
    height = randint(1500, 2000)
    hash = hashlib.sha256(block_hash.encode()).hexdigest()
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

    return block
