import codecs
import hashlib
import logging
import time
from datetime import datetime

from asgiref.base_layer import BaseChannelLayer
from channels import Channel
from django.db import models, IntegrityError, connection
from django.utils.timezone import make_aware

from blocks.pynubitools import bin_to_b58check
from blocks.utils.numbers import get_var_int_bytes, convert_to_satoshis
from daio.models import Coin

logger = logging.getLogger(__name__)


class Transaction(models.Model):
    """
    A transaction within a block
    belongs to one block but can have multiple inputs and outputs
    """
    tx_id = models.CharField(
        max_length=610,
        unique=True,
        db_index=True,
    )
    block = models.ForeignKey(
        'Block',
        blank=True,
        null=True,
        related_name='transactions',
        related_query_name='transaction',
        on_delete=models.SET_NULL,
    )
    index = models.BigIntegerField(
        default=-1
    )
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
        return '{}:{}@{}'.format(self.index, self.tx_id[:8], self.block)

    class Meta:
        ordering = ['index']

    def save(self, *args, **kwargs):
        validate = kwargs.pop('validate', True)

        super(Transaction, self).save(*args, **kwargs)
        if validate:
            if not self.is_valid:
                try:
                    Channel('repair_transaction').send({
                        'chain': connection.tenant.schema_name,
                        'tx_id': self.tx_id
                    })
                except BaseChannelLayer.ChannelFull:
                    logger.error('CHANNEL FULL!')

    @property
    def class_type(self):
        return 'Transaction'

    def parse_rpc_tx(self, rpc_tx):
        logger.info('parsing tx {}'.format(self))
        self.version = rpc_tx.get('version', None)
        tx_time = rpc_tx.get('time', None)

        if tx_time:
            self.time = make_aware(datetime.fromtimestamp(int(tx_time)))
        else:
            self.time = None

        self.lock_time = rpc_tx.get('locktime', None)
        self.unit = rpc_tx.get('unit', None)

        self.save(validate=False)

        # for each input in the transaction, save a TxInput
        vin_index = 0
        for vin in rpc_tx.get('vin', []):
            script_sig = vin.get('scriptSig', {})
            try:
                tx_input = TxInput.objects.get(
                    transaction=self,
                    index=vin_index,
                )
                tx_input.sequence = vin.get('sequence', '')
                tx_input.coin_base = vin.get('coinbase', '')
                tx_input.script_sig_asm = script_sig.get('asm', '')
                tx_input.script_sig_hex = script_sig.get('hex', '')
            except TxInput.DoesNotExist:
                tx_input = TxInput.objects.create(
                    transaction=self,
                    index=vin_index,
                    sequence=vin.get('sequence', ''),
                    coin_base=vin.get('coinbase', ''),
                    script_sig_asm=script_sig.get('asm', ''),
                    script_sig_hex=script_sig.get('hex', ''),
                )

            tx_id = vin.get('txid', None)

            if tx_id:
                # this long tx_id indicates a grant reward.
                # we ignore these as they are effectively coinbase inputs
                if tx_id != '0000000000000000000000000000000000000000000000000000000000000000':  # noqa
                    # input is spending a previous output. Link it here
                    previous_transaction, created = Transaction.objects.get_or_create(
                        tx_id=tx_id
                    )

                    if created:
                        logger.error(
                            'tx {} not found for previous output to {}'.format(
                                tx_id[:8],
                                tx_input
                            )
                        )
                        try:
                            Channel('repair_transaction').send({
                                'chain': connection.schema_name,
                                'tx_id': tx_id
                            })
                        except BaseChannelLayer.ChannelFull:
                            logger.error('CHANNEL FULL!')

                    previous_output, _ = TxOutput.objects.get_or_create(
                        transaction=previous_transaction,
                        index=vin.get('vout'),
                    )

                    tx_input.previous_output = previous_output

            try:
                tx_input.save()
            except IntegrityError as e:
                logger.error(
                    'issue saving tx_input for {}: {}'.format(self, e)
                )
                try:
                    Channel('repair_transaction').send({
                        'chain': connection.schema_name,
                        'tx_id': tx_id
                    })
                except BaseChannelLayer.ChannelFull:
                    logger.error('CHANNEL FULL!')
                return

            vin_index += 1

        # save a TXOutput for each output in the Transaction
        for vout in rpc_tx.get('vout', []):
            script_pubkey = vout.get('scriptPubKey', {})
            try:
                tx_output = TxOutput.objects.get(
                    transaction=self,
                    index=vout.get('n'),
                )
                tx_output.value = convert_to_satoshis(vout.get('value', 0.0))
                # convert to satoshis
                tx_output.script_pub_key_asm = script_pubkey.get('asm', '')
                tx_output.script_pub_key_hex = script_pubkey.get('hex', '')
                tx_output.script_pub_key_type = script_pubkey.get('type', '')
                tx_output.script_pub_key_req_sig = script_pubkey.get('reqSigs', '')
            except TxOutput.DoesNotExist:
                tx_output = TxOutput.objects.create(
                    transaction=self,
                    index=vout.get('n'),
                    value=convert_to_satoshis(vout.get('value', 0.0)),
                    script_pub_key_asm=script_pubkey.get('asm', ''),
                    script_pub_key_hex=script_pubkey.get('hex', ''),
                    script_pub_key_type=script_pubkey.get('type', ''),
                    script_pub_key_req_sig=script_pubkey.get('reqSigs', ''),
                )

            tx_output.save()

            # save each address in the output
            for addr in script_pubkey.get('addresses', []):
                try:
                    Channel('parse_address').send({
                        'chain': connection.schema_name,
                        'address': addr,
                        'tx_output': tx_output.pk
                    })
                except BaseChannelLayer.ChannelFull:
                    logger.error('CHANNEL FULL!')
        self.save()
        logger.info('saved tx {}'.format(self))
        return

    @property
    def is_valid(self):
        valid, message = self.validate()
        return valid

    def validate(self):
        if self.index < 0:
            return False, 'incorrect index'

        for attribute in [
            'self.version',
            'self.time',
            'self.index'
        ]:
            if eval(attribute) is None:
                return False, 'missing attribute: {}'.format(attribute)

        # start off  with version and number of inputs
        tx_bytes = (
            self.version.to_bytes(4, 'little') +
            int(time.mktime(self.time.timetuple())).to_bytes(4, 'little') +
            get_var_int_bytes(self.inputs.all().count())
        )
        # add each input
        for tx_input in self.inputs.all().order_by('index'):
            if tx_input.previous_output:
                tx_input_bytes = (
                    codecs.decode(
                        tx_input.previous_output.transaction.tx_id, 'hex'
                    )[::-1] +
                    tx_input.previous_output.index.to_bytes(4, 'little') +
                    get_var_int_bytes(
                        len(codecs.decode(tx_input.script_sig_hex, 'hex'))) +  # noqa
                    codecs.decode(tx_input.script_sig_hex, 'hex') +
                    tx_input.sequence.to_bytes(4, 'little')
                )
            else:
                # coinbase or custodial grant
                tx_input_bytes = (
                    codecs.decode('0' * 64, 'hex')[::-1] +
                    codecs.decode('f' * 8, 'hex')[::-1] +
                    get_var_int_bytes(len(codecs.decode(tx_input.coin_base, 'hex'))) +
                    codecs.decode(tx_input.coin_base, 'hex') +
                    tx_input.sequence.to_bytes(4, 'little')
                )

            tx_bytes += tx_input_bytes
        # add the number of outputs
        tx_bytes += get_var_int_bytes(self.outputs.all().count())
        # add each output
        for tx_output in self.outputs.all().order_by('index'):
            tx_output_bytes = (
                tx_output.value.to_bytes(8, 'little') +
                get_var_int_bytes(
                    len(codecs.decode(tx_output.script_pub_key_hex, 'hex'))) +  # noqa
                codecs.decode(tx_output.script_pub_key_hex, 'hex')
            )
            tx_bytes += tx_output_bytes
        # add the locktime
        tx_bytes += self.lock_time.to_bytes(4, 'little')
        # add the unit
        tx_bytes += codecs.encode(self.unit)

        # get the he
        # hash the header and fail if it doesn't match the one on record
        header_hash = hashlib.sha256(hashlib.sha256(tx_bytes).digest()).digest()
        calc_hash = codecs.encode(header_hash[::-1], 'hex')
        if str.encode(self.tx_id) != calc_hash:
            return False, 'incorrect hash'

        # check for a block
        if not self.block:
            return False, 'no block'

        # check the outputs for addresses
        for tx_out in self.outputs.all():
            if tx_out.script_pub_key_type == 'pubkey':
                if len(tx_out.script_pub_key_hex) < 50:
                    logger.error('output hex is too short: {}'.format(tx_out))
                # get the unit magic byte
                try:
                    coin = Coin.objects.get(unit_code=self.unit)
                except Coin.DoesNotExist:
                    return False, 'coin for {} does not exist'.format(self.unit)
                # get the output bytes
                tx_out_bytes = codecs.decode(tx_out.script_pub_key_hex, 'hex')
                # calculate the address from the hex
                hex_address = bin_to_b58check(tx_out_bytes[3:23], coin.magic_byte)
                if hex_address != tx_out.address:
                    return False, 'output has wrong address: {} != {}'.format(tx_out.address, hex_address)

        return True, 'Transaction is valid'


class TxOutput(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        related_name='outputs',
        related_query_name='output',
        on_delete=models.CASCADE,
    )
    value = models.BigIntegerField(
        default=0
    )
    index = models.IntegerField()
    script_pub_key_asm = models.TextField(
        blank=True,
        default='',
    )
    script_pub_key_hex = models.TextField(
        blank=True,
        default='',
    )
    script_pub_key_type = models.TextField(
        blank=True,
        default='',
    )
    script_pub_key_req_sig = models.TextField(
        blank=True,
        default='',
    )
    address = models.ForeignKey(
        'Address',
        related_name='output_addresses',
        related_query_name='output_address',
        blank=True,
        null=True,
    )

    def __str__(self):
        return '{}:{}@{}'.format(self.index, self.value, self.transaction)

    class Meta:
        unique_together = ('transaction', 'index')
        ordering = ['-index']

    @property
    def display_value(self):
        return self.value / 10000


class TxInput(models.Model):
    """
    A transaction input.
    Belongs to a single transaction
    """
    transaction = models.ForeignKey(
        Transaction,
        related_name='inputs',
        related_query_name='input',
        on_delete=models.CASCADE,
    )
    index = models.BigIntegerField()
    previous_output = models.OneToOneField(
        TxOutput,
        blank=True,
        null=True,
        related_name='previous_output',
        on_delete=models.SET_NULL,
    )
    coin_base = models.CharField(
        max_length=610,
        blank=True,
    )
    sequence = models.BigIntegerField(
        blank=True,
        default=4294967295,
    )
    script_sig_asm = models.TextField(
        blank=True,
        default='',
    )
    script_sig_hex = models.TextField(
        blank=True,
        default='',
    )

    def __str__(self):
        return '{}@{}'.format(self.index, self.transaction)

    class Meta:
        ordering = ['-index']
        unique_together = ('transaction', 'index')
