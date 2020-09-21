import codecs
import hashlib
import json
import logging
import time
from datetime import datetime

from asgiref.base_layer import BaseChannelLayer
from caching.base import CachingManager, CachingMixin
from channels import Channel, Group
from django.core.cache import cache
from django.db import IntegrityError, connection, models
from django.db.models import Sum
from django.utils.timezone import make_aware

from blocks.utils.numbers import convert_to_satoshis, get_var_int_bytes
from daio.models import Chain, Coin

logger = logging.getLogger(__name__)


class Transaction(CachingMixin, models.Model):
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
        "Block",
        blank=True,
        null=True,
        related_name="transactions",
        related_query_name="transaction",
        on_delete=models.SET_NULL,
    )
    index = models.BigIntegerField(default=-1, db_index=True)
    version = models.IntegerField(
        blank=True,
        null=True,
    )
    time = models.DateTimeField(blank=True, null=True, db_index=True)
    lock_time = models.IntegerField(blank=True, null=True, default=0)
    coin = models.ForeignKey(
        Coin,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="coin",
        related_query_name="coins",
    )

    objects = CachingManager()

    def __str__(self):
        return "{}:{}@{}".format(self.index, self.tx_id[:8], self.block)

    class Meta:
        ordering = ["index"]

    def send_for_repair(self):
        try:
            Channel("repair_transaction").send(
                {"chain": connection.tenant.schema_name, "tx_id": self.tx_id}
            )
        except BaseChannelLayer.ChannelFull:
            logger.error("CHANNEL FULL!")

    def serialize(self):
        serialized_tx = None
        is_valid = self.is_valid

        if is_valid:
            serialized_tx = cache.get(
                "{}_{}".format(connection.tenant.schema_name, self.tx_id)
            )
        else:
            self.send_for_repair()

        if serialized_tx is None:
            serialized_tx = {
                "tx_id": self.tx_id,
                "index": self.index,
                "version": self.version,
                "time": (
                    datetime.strftime(self.time, "%Y-%m-%d %H:%M:%S %Z")
                    if self.time
                    else None
                ),
                "lock_time": self.lock_time,
                "coin": self.coin.code if self.coin else None,
                "inputs": [tx_input.serialize() for tx_input in self.inputs.all()],
                "outputs": [tx_output.serialize() for tx_output in self.outputs.all()],
                "valid": is_valid,
                "total_input": self.total_input,
                "total_output": self.total_output,
                "address_inputs": self.address_inputs,
                "address_outputs": self.address_outputs,
                "balance": self.balance,
                "coinbase": self.is_coinbase,
            }

            if is_valid:
                cache.set(
                    "{}_{}".format(connection.tenant.schema_name, self.tx_id),
                    serialized_tx,
                )

        return serialized_tx

    def save(self, *args, **kwargs):
        validate = kwargs.pop("validate", True)

        try:
            super(Transaction, self).save(*args, **kwargs)
        except IntegrityError as e:
            logger.error(e)
            Transaction.objects.filter(tx_id=self.tx_id).delete()
            self.block = None
            validate = True
            super(Transaction, self).save(*args, **kwargs)

        if validate:
            if not self.is_valid:
                self.send_for_repair()

        logger.info("sending to transaction group")
        Group("{}_transaction".format(connection.tenant.schema_name)).send(
            {
                "text": json.dumps(
                    {
                        "stream": "transaction_update",
                        "payload": {"tx_id": self.tx_id, "tx": self.serialize()},
                    }
                )
            },
            immediately=True,
        )

    @property
    def class_type(self):
        return "Transaction"

    def parse_input(self, vin, vin_index):
        script_sig = vin.get("scriptSig", {})
        try:
            try:
                tx_input = TxInput.objects.get(
                    transaction_id=self.id,
                    index=vin_index,
                )
                tx_input.sequence = vin.get("sequence", "")
                tx_input.coin_base = vin.get("coinbase", "")
                tx_input.script_sig_asm = script_sig.get("asm", "")
                tx_input.script_sig_hex = script_sig.get("hex", "")
            except TxInput.DoesNotExist:
                logger.warning(
                    "input for {}@{} does not exist. creating".format(vin_index, self)
                )
                tx_input = TxInput.objects.create(
                    transaction_id=self.id,
                    index=vin_index,
                    sequence=vin.get("sequence", ""),
                    coin_base=vin.get("coinbase", ""),
                    script_sig_asm=script_sig.get("asm", ""),
                    script_sig_hex=script_sig.get("hex", ""),
                )
        except IntegrityError:
            logger.warning("Integrity Error")
            return

        tx_input.save()

        tx_id = vin.get("txid", None)

        if tx_id:
            # this long tx_id indicates a grant reward.
            # we ignore these as they are effectively coinbase inputs
            if (
                tx_id
                != "0000000000000000000000000000000000000000000000000000000000000000"
            ):  # noqa
                # input is spending a previous output. Link it here
                previous_transaction, created = Transaction.objects.get_or_create(
                    tx_id=tx_id
                )

                if created:
                    logger.error(
                        "tx {} not found for previous output to {}".format(
                            tx_id[:8], tx_input
                        )
                    )
                    try:
                        Channel("repair_transaction").send(
                            {"chain": connection.schema_name, "tx_id": tx_id}
                        )
                    except BaseChannelLayer.ChannelFull:
                        logger.error("CHANNEL FULL!")

                previous_output, _ = TxOutput.objects.get_or_create(
                    transaction_id=previous_transaction.id,
                    index=vin.get("vout"),
                )

                tx_input.previous_output_id = previous_output.id

                try:
                    tx_input.save()
                except IntegrityError:
                    logger.error("output is already used as a previous input")
                    # find the t_in that links this t_out
                    try:
                        t_in = TxInput.objects.get(previous_output=previous_output)
                        t_in.previous_output = None
                        t_in.save()
                    except TxInput.DoesNotExist:
                        # no input found. Just delete the tou instead
                        previous_output.delete()
                        previous_output, _ = TxOutput.objects.get_or_create(
                            transaction_id=previous_transaction.id,
                            index=vin.get("vout"),
                        )
                    tx_input.previous_output_id = previous_output.id
                    tx_input.save()

    def parse_output(self, vout):
        script_pubkey = vout.get("scriptPubKey", {})
        try:
            try:
                tx_output = TxOutput.objects.get(
                    transaction_id=self.id,
                    index=vout.get("n"),
                )
                tx_output.value = convert_to_satoshis(vout.get("value", 0.0))
                # convert to satoshis
                tx_output.script_pub_key_asm = script_pubkey.get("asm", "")
                tx_output.script_pub_key_hex = script_pubkey.get("hex", "")
                tx_output.script_pub_key_type = script_pubkey.get("type", "")
                tx_output.script_pub_key_req_sig = script_pubkey.get("reqSigs", "")
            except TxOutput.DoesNotExist:
                logger.warning(
                    "output for {}@{} does not exist. creating".format(
                        vout.get("n"), self
                    )
                )
                tx_output = TxOutput.objects.create(
                    transaction_id=self.id,
                    index=vout.get("n"),
                    value=convert_to_satoshis(vout.get("value", 0.0)),
                    script_pub_key_asm=script_pubkey.get("asm", ""),
                    script_pub_key_hex=script_pubkey.get("hex", ""),
                    script_pub_key_type=script_pubkey.get("type", ""),
                    script_pub_key_req_sig=script_pubkey.get("reqSigs", ""),
                )

            tx_output.save()

        except IntegrityError:
            logger.warning("Integrity Error")
            return

        # attach the address to the output
        for addr in script_pubkey.get("addresses", []):
            try:
                Channel("parse_address").send(
                    {
                        "chain": connection.schema_name,
                        "address": addr,
                        "tx_output": tx_output.pk,
                    }
                )
            except BaseChannelLayer.ChannelFull:
                logger.error("CHANNEL FULL!")

        # parse park outputs
        if tx_output.script_pub_key_type == "park":
            park_data = script_pubkey.get("park", {})
            tx_output.park_duration = park_data.get("duration")
            tx_output.save()
            try:
                Channel("parse_address").send(
                    {
                        "chain": connection.schema_name,
                        "address": park_data.get("unparkaddress"),
                        "tx_output": tx_output.pk,
                    }
                )
            except BaseChannelLayer.ChannelFull:
                logger.error("CHANNEL FULL!")

    def parse_rpc_tx(self, rpc_tx):
        logger.info("parsing tx {}".format(self))
        self.version = rpc_tx.get("version", None)
        tx_time = rpc_tx.get("time", None)

        if tx_time:
            self.time = make_aware(datetime.fromtimestamp(int(tx_time)))
        else:
            self.time = None

        self.lock_time = rpc_tx.get("locktime", 0)
        self.coin = Coin.objects.get(
            chain=Chain.objects.get(schema_name=connection.schema_name),
            unit_code=rpc_tx.get("unit", None),
        )

        self.save(validate=False)

        # for each input in the transaction, save a TxInput
        vin_index = 0
        for vin in rpc_tx.get("vin", []):
            self.parse_input(vin, vin_index)
            vin_index += 1

        # save a TXOutput for each output in the Transaction
        for vout in rpc_tx.get("vout", []):
            self.parse_output(vout)

        self.save()
        logger.info("saved tx {}".format(self))
        return

    @property
    def is_valid(self):
        valid, message = self.validate()
        return valid

    def validate(self):
        if self.index < 0:
            return False, "incorrect index"

        for attribute in ["self.version", "self.time", "self.index", "self.lock_time"]:
            if eval(attribute) is None:
                return False, "missing attribute: {}".format(attribute)

        # start off  with version and number of inputs
        tx_bytes = (
            self.version.to_bytes(4, "little")
            + int(time.mktime(self.time.timetuple())).to_bytes(4, "little")
            + get_var_int_bytes(self.inputs.all().count())
        )
        # add each input
        for tx_input in self.inputs.all().order_by("index"):
            if tx_input.previous_output:
                tx_input_bytes = (
                    codecs.decode(tx_input.previous_output.transaction.tx_id, "hex")[
                        ::-1
                    ]
                    + tx_input.previous_output.index.to_bytes(4, "little")
                    + get_var_int_bytes(
                        len(codecs.decode(tx_input.script_sig_hex, "hex"))
                    )
                    + codecs.decode(tx_input.script_sig_hex, "hex")  # noqa
                    + tx_input.sequence.to_bytes(4, "little")
                )
            else:
                if tx_input.coin_base:
                    tx_input_bytes = (
                        codecs.decode("0" * 64, "hex")[::-1]
                        + codecs.decode("f" * 8, "hex")[::-1]
                        + get_var_int_bytes(
                            len(codecs.decode(tx_input.coin_base, "hex"))
                        )
                        + codecs.decode(tx_input.coin_base, "hex")
                        + tx_input.sequence.to_bytes(4, "little")
                    )
                else:  # custodial grant
                    tx_input_bytes = (
                        codecs.decode("0" * 64, "hex")[::-1]
                        + codecs.decode(self.coin.vout_n_value, "hex")[::-1]
                        + get_var_int_bytes(
                            len(codecs.decode(tx_input.coin_base, "hex"))
                        )
                        + codecs.decode(tx_input.coin_base, "hex")
                        + tx_input.sequence.to_bytes(4, "little")
                    )
            tx_bytes += tx_input_bytes
        # add the number of outputs
        tx_bytes += get_var_int_bytes(self.outputs.all().count())
        # add each output
        for tx_output in self.outputs.all().order_by("index"):
            tx_output_bytes = (
                tx_output.value.to_bytes(8, "little")
                + get_var_int_bytes(
                    len(codecs.decode(tx_output.script_pub_key_hex, "hex"))
                )
                + codecs.decode(tx_output.script_pub_key_hex, "hex")
            )
            tx_bytes += tx_output_bytes
        # add the locktime

        tx_bytes += self.lock_time.to_bytes(4, "little")
        # add the unit
        tx_bytes += codecs.encode(self.coin.unit_code)

        # hash the header and fail if it doesn't match the one on record
        header_hash = hashlib.sha256(hashlib.sha256(tx_bytes).digest()).digest()
        calc_hash = codecs.encode(header_hash[::-1], "hex")
        if str.encode(self.tx_id) != calc_hash:
            return False, "incorrect hash"

        # check for a block
        if not self.block:
            return False, "no block"

        # check the outputs for addresses
        for tx_out in self.outputs.all():
            if tx_out.script_pub_key_type in ["pubkey", "pubkeyhash", "park"]:
                if not tx_out.address:
                    return False, "output has no address"
            if tx_out.script_pub_key_type == "park":
                if not tx_out.park_duration:
                    return False, "park output has no duration"

        # check the inputs, previous outputs for addresses
        for tx_in in self.inputs.all():
            if tx_in.previous_output:
                if not tx_in.previous_output.address:
                    return False, "address missing from previous output"
                if tx_in.previous_output.value == 0:
                    return False, "previous output value is 0"

        # check for unit/coin
        if not self.coin:
            return False, "no associated coin"

        return True, "Transaction is valid"

    @property
    def total_input(self):
        total_in = 0
        for tin in self.inputs.all():
            if tin.previous_output:
                total_in += tin.previous_output.display_value
        return total_in

    @property
    def total_output(self):
        total_out = 0
        for tout in self.outputs.all():
            total_out += tout.display_value
        return total_out

    @property
    def address_inputs(self):
        if not self.block:
            return

        address_inputs = {}

        for tin in self.inputs.all():
            if not tin.previous_output or not tin.previous_output.address:
                continue
            if tin.previous_output.address.address not in address_inputs:
                address_inputs[tin.previous_output.address.address] = float(0)
            address_inputs[
                tin.previous_output.address.address
            ] += tin.previous_output.display_value  # noqa

        return address_inputs

    @property
    def address_outputs(self):
        if not self.block:
            return

        address_outputs = {}

        for address_tx in (
            self.outputs.all().distinct("address__address").order_by("address__address")
        ):
            if not address_tx.address:
                continue
            address_outputs[address_tx.address.address] = (
                self.outputs.filter(address=address_tx.address).aggregate(Sum("value"))[
                    "value__sum"
                ]
                / 10000
            )

        return address_outputs

    @property
    def balance(self):
        return self.total_output - self.total_input

    @property
    def is_coinbase(self):
        for tin in self.inputs.all():
            if tin.coin_base:
                return True
        return False


class TxOutput(CachingMixin, models.Model):
    transaction = models.ForeignKey(
        Transaction,
        related_name="outputs",
        related_query_name="output",
        on_delete=models.CASCADE,
    )
    value = models.BigIntegerField(default=0)
    index = models.IntegerField(db_index=True)
    script_pub_key_asm = models.TextField(
        blank=True,
        default="",
    )
    script_pub_key_hex = models.TextField(
        blank=True,
        default="",
    )
    script_pub_key_type = models.TextField(
        blank=True,
        default="",
    )
    script_pub_key_req_sig = models.TextField(
        blank=True,
        default="",
    )
    address = models.ForeignKey(
        "Address",
        related_name="outputs",
        related_query_name="output_address",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    park_duration = models.BigIntegerField(
        blank=True,
        null=True,
    )

    objects = CachingManager()

    def __str__(self):
        return "{}:{}@{}".format(self.index, self.value, self.transaction)

    class Meta:
        unique_together = ("transaction", "index")
        ordering = ["index"]

    @property
    def display_value(self):
        return self.value / 10000

    @property
    def is_spent(self):
        try:
            return True
        except TxInput.DoesNotExist:
            return False

    def serialize(self):
        try:
            spent_in = self.input.transaction.block.height
        except (TxInput.DoesNotExist, AttributeError):
            spent_in = None

        return {
            "value": self.value,
            "index": self.index,
            "pub_key_asm": self.script_pub_key_asm,
            "pub_key_hex": self.script_pub_key_hex,
            "pub_key_type": self.script_pub_key_type,
            "pub_key_req_sig": self.script_pub_key_req_sig,
            "address": self.address.address if self.address else None,
            "park_duration": self.park_duration,
            "display_value": self.display_value,
            "spent": self.is_spent,
            "spent_in": spent_in,
            "block_height": self.transaction.block.height
            if self.transaction.block
            else None,
        }


class TxInput(CachingMixin, models.Model):
    """
    A transaction input.
    Belongs to a single transaction
    """

    transaction = models.ForeignKey(
        Transaction,
        related_name="inputs",
        related_query_name="input",
        on_delete=models.CASCADE,
    )
    index = models.BigIntegerField(db_index=True)
    previous_output = models.OneToOneField(
        TxOutput,
        blank=True,
        null=True,
        related_name="input",
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
        default="",
    )
    script_sig_hex = models.TextField(
        blank=True,
        default="",
    )

    objects = CachingManager()

    def __str__(self):
        return "{}@{}".format(self.index, self.transaction)

    class Meta:
        ordering = ["index"]
        unique_together = ("transaction", "index")

    def serialize(self):
        return {
            "index": self.index,
            "previous_output": self.previous_output.serialize()
            if self.previous_output
            else None,
            "coin_base": self.coin_base,
            "sequence": self.sequence,
            "sig_asm": self.script_sig_asm,
            "sig_hex": self.script_sig_hex,
        }
