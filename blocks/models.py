from __future__ import unicode_literals

import hashlib
from datetime import datetime
from decimal import Decimal

import logging
import time
import codecs
from channels import Channel
from django.db import IntegrityError
from django.db import models
from django.utils.timezone import make_aware

from blocks.utils.numbers import get_var_int_bytes


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
        blank=True,
        null=True,
        unique=True,
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
        logger = logging.getLogger('block_parser')
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
        # check hash is correct for data
        # first check the header attributes
        for attribute in [
            self.version,
            self.previous_block,
            self.merkle_root,
            self.time,
            self.bits,
            self.nonce
        ]:
            if attribute is None:
                return False, 'missing attribute'

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


class Transaction(models.Model):
    """
    A transaction within a block
    belongs to one block but can have multiple inputs and outputs
    """
    block = models.ForeignKey(
        Block,
        related_name='transactions',
        related_query_name='transaction',
        null=True,
        on_delete=models.SET_NULL,
    )
    tx_id = models.CharField(
        max_length=610,
        unique=True,
    )
    index = models.BigIntegerField()
    version = models.IntegerField(
        blank=True,
        null=True,
    )
    time = models.DateTimeField(
        blank=True,
        null=True,
    )
    lock_time = models.IntegerField(
        blank=True,
        null=True,
    )
    unit = models.CharField(
        max_length=15,
        blank=True,
        null=True,
    )

    def __str__(self):
        return str(self.tx_id)

    @property
    def class_type(self):
        return 'Transaction'
    
    def parse_rpc_tx(self, rpc_tx):
        logger = logging.getLogger('block_parser')
        logger.info('parsing tx {}'.format(self.tx_id))
        self.version = rpc_tx.get('version', None)
        tx_time = rpc_tx.get('time', None)

        if tx_time:
            self.time = make_aware(datetime.fromtimestamp(int(tx_time)))
        else:
            self.time = None

        self.lock_time = rpc_tx.get('locktime', None)
        self.unit = rpc_tx.get('unit', None)
        self.save()

        # for each input in the transaction, save a TxInput
        for vin in rpc_tx.get('vin', []):
            tx_input, _ = TxInput.objects.get_or_create(
                transaction=self,
            )

            tx_input.sequence = vin.get('sequence', None)
            tx_input.coin_base = vin.get('coinbase', None)

            script_sig = vin.get('scriptSig', {})
            tx_input.script_sig_asm = script_sig.get('asm', None)
            tx_input.script_sig_hex = script_sig.get('hex', None)

            tx_id = vin.get('txid', None)

            if tx_id:
                # input is spending a previous output. Link it here
                try:
                    previous_transaction = Transaction.objects.get(tx_id=tx_id)
                except Transaction.DoesNotExist:
                    logger.error(
                        'Tx not found for previous output: {} in {}'.format(tx_id, vin)
                    )
                    continue

                output_index = vin.get('vout', None)
                if output_index is None:
                    logger.error(
                        'No previous index found: {} in {}'.format(output_index, vin)
                    )
                    continue

                try:
                    previous_output = TxOutput.objects.get(
                        transaction=previous_transaction,
                        index=output_index,
                    )
                except TxOutput.DoesNotExist:
                    previous_output = None

                tx_input.previous_output = previous_output

        # save a TXOutput for each output in the Transaction
        for vout in rpc_tx.get('vout', []):
            tx_output, _ = TxOutput.objects.get_or_create(
                transaction=self,
                value=vout.get('value', 0) * 100000000,  # convert to satoshis
                index=vout.get('n', -1),
            )
            script_pubkey = vout.get('scriptPubKey', {})
            tx_output.script_pub_key_asm = script_pubkey.get('asm', None)
            tx_output.script_pub_key_hex = script_pubkey.get('hex', None)
            tx_output.script_pub_key_type = script_pubkey.get('type', None)
            tx_output.script_pub_key_req_sig = script_pubkey.get('reqSigs', None)

            # save each address in the output
            for addr in script_pubkey.get('addresses', []):
                address, created = Address.objects.get_or_create(
                    address=addr,
                )
                if created:
                    address.save()
                tx_output.addresses.add(address)
                tx_output.save()
                # TODO check the address against the list of addresses to watch
                # check_thread = Thread(
                #     target=self.check_watch_addresses,
                #     kwargs={
                #         'address': address,
                #         'value': tx_output.value,
                #     }
                # )
                # check_thread.daemon = True
                # check_thread.start()
        logger.info('saved tx {}'.format(self.tx_id))
        return

    def validate(self):
        # start off  with version and number of inputs
        tx_bytes = [
            self.version.to_bytes(4, 'little') +
            get_var_int_bytes(self.inputs.all().count())
        ]
        # add each input
        for tx_input in self.inputs.all():
            tx_input_bytes = [
                codecs.decode(tx_input.tx_id, 'hex')[::-1] +
                tx_input.v_out.to_bytes(4, 'little') +
                get_var_int_bytes(len(tx_input.script_sig_hex)) +
                codecs.decode(tx_input.script_sig_hex, 'hex')[::-1] +
                tx_input.sequence.to_bytes(4, 'little')
            ]
            tx_bytes += tx_input_bytes
        # add the number of outputs
        tx_bytes += get_var_int_bytes(self.outputs.all().count())
        # add each output
        for tx_output in self.outputs.all():
            tx_output_bytes = [
                tx_output.value.to_bytes(8, 'little') +
                get_var_int_bytes(len(tx_output.script_pub_key_hex)) +
                codecs.decode(tx_output.script_pub_key_hex, 'hex')[::-1]
            ]
            tx_bytes += tx_output_bytes
        # add the locktime
        tx_bytes += self.lock_time.to_bytes(4, 'little')
        print(tx_bytes)


class Address(models.Model):
    address = models.CharField(
        max_length=610,
        unique=True,
    )

    def __str__(self):
        return str(self.address)

    @property
    def class_type(self):
        return 'Address'

    @property
    def balance(self):
        value = Decimal(0.0)
        # get the outputs for the address
        outputs = TxOutput.objects.filter(
            addresses__address=self.address,
        )
        for output in outputs:
            value += Decimal(output.value)
        return value


class TxOutput(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        null=True,
        related_name='outputs',
        related_query_name='output',
        on_delete=models.SET_NULL,
    )
    value = models.BigIntegerField(
        default=0
    )
    index = models.IntegerField()
    script_pub_key_asm = models.TextField(
        blank=True,
        null=True,
    )
    script_pub_key_hex = models.TextField(
        blank=True,
        null=True,
    )
    script_pub_key_type = models.TextField(
        blank=True,
        null=True,
    )
    script_pub_key_req_sig = models.TextField(
        blank=True,
        null=True,
    )
    addresses = models.ManyToManyField(
        Address,
        related_name='output_addresses',
        related_query_name='tx_output',
    )

    def __str__(self):
        return str(self.pk)

    def Meta(self):
        self.unique_together = (self.transaction, self.index)


class TxInput(models.Model):
    """
    A transaction input.
    Belongs to a single transaction
    """
    transaction = models.ForeignKey(
        Transaction,
        null=True,
        related_name='inputs',
        related_query_name='input',
        on_delete=models.SET_NULL,
    )
    previous_output = models.OneToOneField(
        TxOutput,
        null=True,
        blank=True,
        related_name='previous_output',
        on_delete=models.SET_NULL,
    )
    coin_base = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    sequence = models.BigIntegerField(
        blank=True,
        null=True,
    )
    script_sig_asm = models.TextField(
        blank=True,
        null=True,
    )
    script_sig_hex = models.TextField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return str(self.pk)


class CustodianVote(models.Model):
    pass


class MotionVote(models.Model):
    pass


class ParkRateVote(models.Model):
    pass


class FeesVote(models.Model):
    pass


class ParkRate(models.Model):
    pass


class WatchAddress(models.Model):
    address = models.ForeignKey(
        Address,
        related_name='watch_addresses',
        related_query_name='watch_address',
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=6
    )
    call_back = models.URLField(
        max_length=610,
    )
    complete = models.BooleanField(
        default=False,
    )
