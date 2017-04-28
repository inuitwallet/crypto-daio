import codecs
import hashlib
import logging
import time
from datetime import datetime

from channels import Channel
from django.db import models, IntegrityError
from django.utils.timezone import make_aware

logger = logging.getLogger('daio')


class Block(models.Model):
    """
    Object definition of a block
    """
    hash = models.CharField(
        max_length=610,
        unique=True,
    )
    size = models.BigIntegerField(
        blank=True,
        null=True,
    )
    height = models.BigIntegerField(
        unique=True,
        blank=True,
        null=True,
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
        return str(self.hash)

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
        if not self.height:
            self.height = rpc_block.get('height', None)
        logger.info('parsing {} at height {}'.format(self.hash, self.height))
        # parse the json and apply to the block we just fetched
        self.size = rpc_block.get('size', None)
        self.version = rpc_block.get('version', None)
        self.merkle_root = rpc_block.get('merkleroot', None)
        self.time = make_aware(
            datetime.strptime(
                rpc_block.get('time', None),
                '%Y-%m-%d %H:%M:%S %Z'
            )
        )
        self.nonce = rpc_block.get('nonce', None)
        self.bits = rpc_block.get('bits', None)
        self.difficulty = rpc_block.get('difficulty', None)
        self.mint = rpc_block.get('mint', None)
        self.flags = rpc_block.get('flags', None)
        self.proof_hash = rpc_block.get('proofhash', None)
        self.entropy_bit = rpc_block.get('entropybit', None)
        self.modifier = rpc_block.get('modifier', None)
        self.modifier_checksum = rpc_block.get('modifierchecksum', None)
        self.coinage_destroyed = rpc_block.get('coinagedestroyed', None)

        self.save()
        # using the previousblockhash, get the block object to connect
        prev_block_hash = rpc_block.get('previousblockhash', None)
        if prev_block_hash:
            previous_block, created = Block.objects.get_or_create(
                hash=prev_block_hash
            )
            self.previous_block = previous_block
            # update the previous block with this block as its next block
            previous_block.next_block = self
            if previous_block.height:
                self.height = previous_block.height + 1
            previous_block.save()
            if created:
                logger.warning(
                    'previous block {} wasn\'t found'.format(previous_block.hash)
                )
                Channel('parse_block').send({'block_hash': prev_block_hash})

        self.save()
        # do the same for the next block
        next_block_hash = rpc_block.get('nextblockhash', None)
        if next_block_hash:
            next_block, created = Block.objects.get_or_create(
                hash=next_block_hash
            )
            self.next_block = next_block
            self.next_block.height = self.height + 1
            next_block.save()
            Channel('parse_block').send({'block_hash': next_block_hash})

        # attempt to save this block. Orphan blocks can appear which ruins data integrity
        # if we find a previous block with the same height already exists we check the
        # hashes of both. If they differ we prefer the newer block as we can assume
        # it has come directly from, the coin daemon.
        try:
            self.save()
            logger.info('saved block {}'.format(self.height))
        except IntegrityError:
            logger.info('block {} already exists'.format(self.height))
            existing_block = Block.objects.get(height=self.height)
            if existing_block.hash != self.hash:
                for transaction in existing_block.transactions.all():
                    for tx_input in transaction.inputs.all():
                        tx_input.delete()
                    for tx_output in transaction.outputs.all():
                        tx_output.delete()
                    transaction.delete()
                existing_block.delete()
                self.save()
                logger.info('saved new block {}'.format(self.height))
            else:
                logger.info(
                    'hashes match. leaving existing block {}'.format(
                        existing_block.height)
                )

        # now we do the transactions
        index = 0
        for tx_hash in rpc_block.get('tx', []):
            Channel('parse_transaction').send(
                {'tx_hash': tx_hash, 'block_hash': self.hash, 'tx_index': index}
            )
            index += 1

    @property
    def is_valid(self):
        valid, message = self.validate()
        return valid

    def validate(self):
        if self.height == 0:
            return True, 'Genesis Block'

        # check hash is correct for data
        # first check the header attributes

        for attribute in [
            'self.version',
            'self.previous_block',
            'self.merkle_root',
            'self.time',
            'self.bits',
            'self.nonce'
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

        # check that previous block height is this height-1
        if self.previous_block.height != (self.height - 1):
            return False, 'incorrect previous height'

        if self.next_block:
            if self.next_block.height != (self.height + 1):
                return False, 'incorrect next height'

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
        if self.flags == 'proof-of-stake':
            tx = self.transactions.get(index=1)
            tx_output = tx.outputs.get(index=1)
            return tx_output.addresses.all()[0]
        else:
            tx = self.transactions.get(index=0)
            tx_output = tx.outputs.get(index=0)
            return tx_output.addresses.all()[0]

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
