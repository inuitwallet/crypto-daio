import codecs
import hashlib
import logging
import time
from datetime import datetime

from channels import Channel
from django.db import models
from django.utils.timezone import make_aware

from blocks.models import Address, Block
from blocks.utils.numbers import get_var_int_bytes

logger = logging.getLogger('daio')


class Transaction(models.Model):
    """
    A transaction within a block
    belongs to one block but can have multiple inputs and outputs
    """
    tx_id = models.CharField(
        max_length=610,
    )
    block = models.ForeignKey(
        Block,
        related_name='transactions',
        related_query_name='transaction',
        on_delete=models.CASCADE,
    )
    index = models.BigIntegerField(
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
        return str(self.tx_id)

    def Meta(self):
        unique_together = (self.block, self.tx_id)

    @property
    def class_type(self):
        return 'Transaction'

    def parse_rpc_tx(self, rpc_tx):
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
        vin_index = 0
        for vin in rpc_tx.get('vin', []):
            script_sig = vin.get('scriptSig', {})
            try:
                tx_input = TxInput.objects.get(
                    transaction=self,
                    index=vin_index,
                )
                tx_input.sequence = vin.get('sequence', None)
                tx_input.coin_base = vin.get('coinbase', None)
                tx_input.script_sig_asm = script_sig.get('asm', '')
                tx_input.script_sig_hex = script_sig.get('hex', '')
            except TxInput.DoesNotExist:
                tx_input = TxInput.objects.create(
                    transaction=self,
                    index=vin_index,
                    sequence=vin.get('sequence', None),
                    coin_base=vin.get('coinbase', None),
                    script_sig_asm=script_sig.get('asm', ''),
                    script_sig_hex=script_sig.get('hex', ''),
                )

            tx_id = vin.get('txid', None)

            if tx_id:
                # input is spending a previous output. Link it here
                try:
                    previous_transaction = Transaction.objects.get(tx_id=tx_id)
                except Transaction.DoesNotExist:
                    logger.error(
                        'Tx not found for previous output: {} in {}'.format(tx_id, vin)
                    )
                    Channel('parse_transaction').send({'tx_hash': tx_id})
                    continue
                except Transaction.MultipleObjectsReturned:
                    logger.error(
                        'Multiple TXs found. Deleting and re-scanning'
                    )
                    Transaction.objects.filter(tx_id=tx_id).delete()
                    Channel('parse_transaction').send({'tx_hash': tx_id})
                    continue

                output_index = vin.get('vout', None)
                if output_index is None:
                    logger.error(
                        'No previous index found: {} in {}'.format(output_index, vin)
                    )
                    Channel('parse_transaction').send({'tx_hash': tx_id})
                    continue

                try:
                    previous_output = TxOutput.objects.get(
                        transaction=previous_transaction,
                        index=output_index,
                    )
                except TxOutput.DoesNotExist:
                    logger.error(
                        'Couldn\'t find previous output for {} at {}'.format(
                            previous_transaction,
                            output_index
                        )
                    )
                    Channel('parse_transaction').send({'tx_hash': tx_id})
                    continue

                tx_input.previous_output = previous_output

            tx_input.save()
            vin_index += 1

        # save a TXOutput for each output in the Transaction
        for vout in rpc_tx.get('vout', []):
            script_pubkey = vout.get('scriptPubKey', {})
            try:
                tx_output = TxOutput.objects.get(
                    transaction=self,
                    index=vout.get('n', -1),
                )
                tx_output.value = vout.get('value', 0) * 100000000  # convert to satoshis
                tx_output.script_pub_key_asm = script_pubkey.get('asm', '')
                tx_output.script_pub_key_hex = script_pubkey.get('hex', '')
                tx_output.script_pub_key_type = script_pubkey.get('type', '')
                tx_output.script_pub_key_req_sig = script_pubkey.get('reqSigs', '')
            except TxOutput.DoesNotExist:
                tx_output = TxOutput.objects.create(
                    transaction=self,
                    index=vout.get('n', -1),
                    value=vout.get('value', 0) * 10000,  # convert to satoshis
                    script_pub_key_asm=script_pubkey.get('asm', ''),
                    script_pub_key_hex=script_pubkey.get('hex', ''),
                    script_pub_key_type=script_pubkey.get('type', ''),
                    script_pub_key_req_sig=script_pubkey.get('reqSigs', ''),
                )

            tx_output.save()

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

    @property
    def is_valid(self):
        valid, message = self.validate()
        return valid

    def validate(self):
        for attribute in [
            self.version,
            self.time
        ]:
            if attribute is None:
                return False, 'missing attribute'

        if self.index < 0:
            return False, 'incorrect index'

        for tx_input in self.inputs.all():
            if tx_input.index < 0:
                return False, 'incorrect input index'

        # start off  with version and number of inputs
        tx_bytes = (
            self.version.to_bytes(4, 'little') +
            int(time.mktime(self.time.timetuple())).to_bytes(4, 'little') +
            get_var_int_bytes(self.inputs.all().count())
        )
        # add each input
        for tx_input in self.inputs.all().order_by('index'):
            if tx_input.coin_base:
                # coinbase
                tx_input_bytes = (
                    codecs.decode('0' * 64, 'hex')[::-1] +
                    codecs.decode('f' * 8, 'hex')[::-1] +
                    get_var_int_bytes(len(codecs.decode(tx_input.coin_base, 'hex'))) +
                    codecs.decode(tx_input.coin_base, 'hex') +
                    tx_input.sequence.to_bytes(4, 'little')
                )
            else:
                if not tx_input.previous_output:
                    return False, 'Input at index {} has no previous output'.format(
                        tx_input.index
                    )
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
            return False, 'incorrect hash {} != {}'.format(
                str.encode(self.tx_id),
                calc_hash
            )

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
        null=True,
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
        return str(self.pk)
