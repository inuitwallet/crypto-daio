import codecs
import hashlib
import logging
import time
from datetime import datetime

from channels import Channel
from django.db import models, connection, IntegrityError
from django.utils.timezone import make_aware

from blocks.utils.rpc import send_rpc, get_block_hash

logger = logging.getLogger(__name__)


class Block(models.Model):
    """
    Object definition of a block
    """
    hash = models.CharField(
        max_length=610,
        unique=True,
        db_index=True,
    )
    size = models.BigIntegerField(
        blank=True,
        null=True,
    )
    height = models.BigIntegerField(
        unique=True,
        blank=True,
        null=True,
        db_index=True,
    )
    version = models.BigIntegerField(
        blank=True,
        null=True,
    )
    merkle_root = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    time = models.DateTimeField(
        blank=True,
        null=True,
    )
    nonce = models.BigIntegerField(
        blank=True,
        null=True,
    )
    bits = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    difficulty = models.FloatField(
        blank=True,
        null=True,
    )
    mint = models.FloatField(
        blank=True,
        null=True,
    )
    previous_block = models.ForeignKey(
        'Block',
        related_name='previous',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    next_block = models.ForeignKey(
        'Block',
        related_name='next',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    flags = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    proof_hash = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    entropy_bit = models.BigIntegerField(
        blank=True,
        null=True,
    )
    modifier = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    modifier_checksum = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    coinage_destroyed = models.BigIntegerField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return '{}:{}'.format(self.height, self.hash[:8])

    def save(self, *args, **kwargs):
        super(Block, self).save(*args, **kwargs)

        if not self.is_valid:
            Channel('repair_block').send({
                'chain': connection.tenant.schema_name,
                'block_hash': self.hash
            })
        else:
            # block is valid. validate the transactions too
            for tx in self.transactions.all():
                if not tx.is_valid:
                    Channel('repair_transaction').send({
                        'chain': connection.tenant.schema_name,
                        'tx_id': tx.tx_id
                    })

    @property
    def class_type(self):
        return 'Block'

    def serialize(self):
        return {
            'height': self.height,
            'size': self.size,
            'version': self.version,
            'merkleroot': self.merkle_root,
            'time': (
                datetime.strftime(
                    self.time,
                    '%Y-%m-%d %H:%M:%S %Z'
                ) if self.time else None
            ),
            'nonce': self.nonce,
            'bits': self.bits,
            'difficulty': self.difficulty,
            'mint': self.mint,
            'flags': self.flags,
            'proofhash': self.proof_hash,
            'entropybit': self.entropy_bit,
            'modifier': self.modifier,
            'modifierchecksum': self.modifier_checksum,
            'coinagedestroyed': self.coinage_destroyed,
            'previousblockhash': (
                self.previous_block.hash if self.previous_block else None
            ),
            'nextblockhash': (
                self.next_block.hash if self.next_block else None
            ),
        }

    def parse_rpc_block(self, rpc_block):
        proposed_height = rpc_block.get('height')
        # check there's no existing block at this height with a different hash
        existing_blocks = Block.objects.filter(height=proposed_height)
        for existing_block in existing_blocks:
            if existing_block.hash != rpc_block.get('hash'):
                logger.warning(
                    'found existing block at height {} with different hash: '
                    'deleting {}'.format(
                        proposed_height,
                        existing_block
                    )
                )
                existing_block.delete()

        self.height = proposed_height
        logger.info('parsing block {}'.format(self))
        # parse the json and apply to the block we just fetched
        self.size = rpc_block.get('size')
        self.version = rpc_block.get('version')
        self.merkle_root = rpc_block.get('merkleroot')
        block_time = rpc_block.get('time')
        if block_time:
            self.time = make_aware(
                datetime.strptime(
                    block_time,
                    '%Y-%m-%d %H:%M:%S %Z'
                )
            )
        self.nonce = rpc_block.get('nonce')
        self.bits = rpc_block.get('bits')
        self.difficulty = rpc_block.get('difficulty')
        self.mint = rpc_block.get('mint')
        self.flags = rpc_block.get('flags')
        self.proof_hash = rpc_block.get('proofhash')
        self.entropy_bit = rpc_block.get('entropybit')
        self.modifier = rpc_block.get('modifier')
        self.modifier_checksum = rpc_block.get('modifierchecksum')
        self.coinage_destroyed = rpc_block.get('coinagedestroyed')

        # using the previousblockhash, get the block object to connect
        prev_block_hash = rpc_block.get('previousblockhash')
        # genesis block has no previous block
        if prev_block_hash:
            previous_block, created = Block.objects.get_or_create(
                hash=prev_block_hash
            )
            self.previous_block = previous_block
            self.previous_block.next_block = self
            self.previous_block.save()

        # do the same for the next block
        next_block_hash = rpc_block.get('nextblockhash')
        if next_block_hash:
            # top block has no next block yet
            next_block, created = Block.objects.get_or_create(
                hash=next_block_hash
            )
            self.next_block = next_block
            self.next_block.previous_block = self
            self.next_block.save()

        # save triggers the validation
        self.save()

        # now we do the transactions
        tx_index = 0
        for tx_id in rpc_block.get('tx', []):
            Channel('parse_transaction').send({
                'chain': connection.tenant.schema_name,
                'tx_id': tx_id,
                'block_hash': self.hash,
                'tx_index': tx_index
            })
            tx_index += 1
        logger.info('saved block {}'.format(self))

    @property
    def is_valid(self):
        valid, message = self.validate()
        return valid

    def validate(self):
        if self.height == 0:
            return True, 'Genesis Block'

        # check hash is corr-
        # first check the header attributes

        for attribute in [
            'self.height',
            'self.version',
            'self.previous_block',
            'self.merkle_root',
            'self.time',
            'self.bits',
            'self.nonce',
        ]:
            if eval(attribute) is None:
                return False, 'missing attribute: {}'.format(attribute)

        # check the previous block has a hash
        if not self.previous_block.hash:
            return False, 'no previous block hash'

        # calculate the header in bytes (little endian)
        header_bytes = (
            self.version.to_bytes(4, 'little') +
            codecs.decode(self.previous_block.hash, 'hex')[::-1] +
            codecs.decode(self.merkle_root, 'hex')[::-1] +
            int(time.mktime(self.time.timetuple())).to_bytes(4, 'little') +
            codecs.decode(self.bits, 'hex')[::-1] +
            self.nonce.to_bytes(4, 'little')
        )

        # hash the header and fail if it doesn't match the one on record
        header_hash = hashlib.sha256(hashlib.sha256(header_bytes).digest()).digest()
        calc_hash = codecs.encode(header_hash[::-1], 'hex')
        if str.encode(self.hash) != calc_hash:
            return False, 'incorrect hash'

        # check that previous block height is this height - 1
        if self.previous_block.height != (self.height - 1):
            return False, 'incorrect previous height'

        # check the previous block next block is this block
        if self.previous_block.next_block != self:
            return False, 'previous block does not point to this block'

        # check the next block height is this height + 1
        if self.next_block:
            if self.next_block.height != (self.height + 1):
                return False, 'incorrect next height'

            # check the next block has this block as it's previous block
            if self.next_block.previous_block != self:
                return False, 'next block does not lead on from this block'

        # calculate merkle root of transactions
        transactions = list(
            self.transactions.all().order_by('index').values_list('tx_id', flat=True)
        )
        merkle_root = self._calculate_merkle_root(transactions)
        if type(merkle_root) == bytes:
            merkle_root = merkle_root.decode()
        if merkle_root != self.merkle_root:
            return False, 'merkle root incorrect'

        return True, 'Block is valid'

    def _calculate_merkle_root(self, hash_list):
        def merkle_hash(a, b):
            # Reverse inputs before and after hashing
            # due to big-endian / little-endian nonsense
            a1 = codecs.decode(a, 'hex')[::-1]
            b1 = codecs.decode(b, 'hex')[::-1]
            h = hashlib.sha256(hashlib.sha256(a1 + b1).digest()).digest()
            return codecs.encode(h[::-1], 'hex')

        if not hash_list:
            return ''.encode()
        if len(hash_list) == 1:
            return hash_list[0]
        new_hash_list = []
        # Process pairs. For odd length, the last is skipped
        for i in range(0, len(hash_list) - 1, 2):
            new_hash_list.append(merkle_hash(hash_list[i], hash_list[i + 1]))
        if len(hash_list) % 2 == 1:  # odd, hash last item twice
            new_hash_list.append(merkle_hash(hash_list[-1], hash_list[-1]))
        return self._calculate_merkle_root(new_hash_list)

    @property
    def solved_by(self):
        index = 0

        if self.flags == 'proof-of-stake':
            index = 1

        for tx in self.transactions.all():
            if tx.index == index:
                for tx_out in tx.outputs.all():
                    if tx_out.index == index:
                        if tx_out.addresses.all().count() >= 1:
                            return tx_out.addresses.all()[0]
        return ''

    @property
    def total_nsr(self):
        total_nsr = 0
        for tx in self.transactions.all():
            for txout in tx.outputs.all():
                if tx.unit == 'S':
                    total_nsr += txout.value
        return total_nsr / 10000

    @property
    def total_nbt(self):
        total_nbt = 0
        for tx in self.transactions.all():
            for txout in tx.outputs.all():
                if tx.unit == 'B':
                    total_nbt += txout.value
        return total_nbt / 10000


class Info(models.Model):
    unit = models.CharField(
        max_length=255
    )
    max_height = models.BigIntegerField()
    money_supply = models.DecimalField(
        max_digits=16,
        decimal_places=4
    )
    total_parked = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        blank=True,
        null=True
    )
    connections = models.BigIntegerField()
    difficulty = models.DecimalField(
        max_digits=16,
        decimal_places=10
    )
    pay_tx_fee = models.DecimalField(
        max_digits=16,
        decimal_places=4
    )
    time_added = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return '{}:{}@{}'.format(self.unit, self.max_height, self.time_added)
