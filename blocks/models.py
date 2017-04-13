from __future__ import unicode_literals

import hashlib
from datetime import datetime
from decimal import Decimal

import logging

import struct
import time
import codecs
from channels import Channel
from django.db import IntegrityError
from django.db import models
from django.utils.timezone import make_aware


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

        # now get the transaction hashes and request their data from the daemon
        # for tx_hash in rpc_block.get('tx', []):
        #     logger.info('scanning tx {}'.format(tx_hash))
        #     # trigger_transaction_parse(self, tx_hash)

    def validate(self):
        # check hash is correct for data
        # first check the header attributes
        for attribute in [
            self.version,
            self.previous_block,
            self.next_block,
            self.merkle_root,
            self.time,
            self.bits,
            self.nonce
        ]:
            if not attribute:
                return False

        # check the previous block has a hash
        if not self.previous_block.hash:
            return False

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
            return False

        # check that previous block height is this height-1
        if self.previous_block.height != (self.height - 1):
            return False

        if self.next_block.height != (self.height + 1):
            return False


class Transaction(models.Model):
    """
    A transaction within a block
    belongs to one block but can have multiple inputs and outputs
    """
    block = models.ForeignKey(
        Block,
        related_name='transactions',
        related_query_name='transaction',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    tx_id = models.CharField(
        max_length=610,
        unique=True,
    )
    version = models.IntegerField(
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
    is_coin_base = models.NullBooleanField()
    is_coin_stake = models.NullBooleanField()

    def __str__(self):
        return str(self.tx_id)

    @property
    def class_type(self):
        return 'Transaction'
    
    def parse_rpc_tx(self, rpc_tx):
        logger = logging.getLogger('block_parser')
        logger.info('parsing tx {}'.format(self.tx_id))
        self.version = rpc_tx.get('version', None)
        self.lock_time = rpc_tx.get('locktime', None)
        self.unit = rpc_tx.get('unit', None)
        self.save()
        # for each input in the transaction, save a TxInput
        for vin in rpc_tx.get('vin', []):
            try:
                output_transaction = Transaction.objects.get(tx_id=vin.get('txid', None))
            except self.DoesNotExist:
                output_transaction = None
            script_sig = vin.get('scriptSig', {})
            tx_input, _ = TxInput.objects.get_or_create(
                transaction=self,
                output_transaction=output_transaction,
                v_out=vin.get('vout', None),
                sequence=vin.get('sequence', None),
                coin_base=vin.get('coinbase', None),
                script_sig_asm=script_sig.get('asm', None),
                script_sig_hex=script_sig.get('hex', None),
            )
            # if a previous output is used as this input, update it's `is_unspent` status
            try:
                spent_output = TxOutput.objects.get(
                    transaction=tx_input.output_transaction,
                    n=tx_input.v_out,
                )
                spent_output.is_unspent = False
                spent_output.save()
            except TxOutput.DoesNotExist:
                continue
        # similar for each TxOutput
        for vout in rpc_tx.get('vout', []):
            script_pubkey = vout.get('scriptPubKey', {})
            tx_output, _ = TxOutput.objects.get_or_create(
                transaction=self,
                value=vout.get('value', 0),
                n=vout.get('n', None),
                script_pub_key_asm=script_pubkey.get('asm', None),
                script_pub_key_hex=script_pubkey.get('hex', None),
                script_pub_key_type=script_pubkey.get('type', None),
                script_pub_key_req_sig=script_pubkey.get('reqSigs', None),
            )
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


class TxInput(models.Model):
    """
    A transaction input.
    Belongs to a single transaction
    """
    transaction = models.ForeignKey(
        Transaction,
        related_name='inputs',
        related_query_name='input',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    tx_id = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    output_transaction = models.ForeignKey(
        Transaction,
        related_name='inout_txs',
        related_query_name='inout_tx',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    v_out = models.BigIntegerField(
        blank=True,
        null=True,
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

    def Meta(self):
        self.unique_together = (self.tx_id, self.v_out)


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
            is_unspent=True,
        )
        for output in outputs:
            value += Decimal(output.value)
        return value


class TxOutput(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        related_name='outputs',
        related_query_name='output',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    value = models.FloatField()
    n = models.IntegerField()
    script_pub_key_asm = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    script_pub_key_hex = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    script_pub_key_type = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    script_pub_key_req_sig = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    addresses = models.ManyToManyField(
        Address,
        related_name='output_addresses',
        related_query_name='tx_output',
    )
    is_unspent = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return str(self.pk)

    def Meta(self):
        self.unique_together = (self.transaction, self.n)
        ordering = '-n'


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
