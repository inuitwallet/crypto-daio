import codecs
import hashlib
import logging
import time
from datetime import datetime


from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import connection, models
from django.db.models import Sum
from django.utils.timezone import make_aware

from blocks.utils.numbers import convert_to_satoshis, get_var_int_bytes
from daio.celery import app
from daio.models import Chain, Coin

logger = logging.getLogger(__name__)


class Transaction(models.Model):
    """
    A transaction within a block
    belongs to one block but can have multiple inputs and outputs
    """

    tx_id = models.CharField(max_length=610, unique=True, db_index=True,)
    block = models.ForeignKey(
        "Block",
        blank=True,
        null=True,
        related_name="transactions",
        related_query_name="transaction",
        on_delete=models.SET_NULL,
    )
    index = models.BigIntegerField(default=-1, db_index=True)
    version = models.IntegerField(blank=True, null=True,)
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
    is_valid = models.BooleanField(default=False)
    validity_errors = ArrayField(
        base_field=models.CharField(max_length=150), blank=True, null=True
    )

    def __str__(self):
        return "{}:{}@{}".format(self.index, self.tx_id[:8], self.block)

    class Meta:
        ordering = ["index"]

    def send_for_repair(self):
        app.send_task(
            "blocks.tasks.transactions.validate_transaction",
            kwargs={"tx_id": self.tx_id},
            queue="high_priority",
        )

    def serialize(self):
        serialized_tx = None
        self.validate()

        if self.is_valid:
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
                "valid": self.is_valid,
                "total_input": self.total_input,
                "total_output": self.total_output,
                "address_inputs": self.address_inputs,
                "address_outputs": self.address_outputs,
                "balance": self.balance,
                "coinbase": self.is_coinbase,
            }

            self.validate()

            if self.is_valid:
                cache.set(
                    "{}_{}".format(connection.tenant.schema_name, self.tx_id),
                    serialized_tx,
                )

        return serialized_tx

    @property
    def class_type(self):
        return "Transaction"

    def parse_input(self, vin, vin_index):
        script_sig = vin.get("scriptSig", {})

        # get the input
        tx_input, _ = TxInput.objects.get_or_create(transaction=self, index=vin_index,)

        # update the details form the vin dict
        tx_input.sequence = vin.get("sequence", "")
        tx_input.coin_base = vin.get("coinbase", "")
        tx_input.script_sig_asm = script_sig.get("asm", "")
        tx_input.script_sig_hex = script_sig.get("hex", "")
        tx_input.save()

        # check the previous transaction
        prev_tx_id = vin.get("txid")

        if prev_tx_id:
            # this long tx_id indicates a grant reward.
            # we ignore these as they are effectively coinbase inputs
            if (
                prev_tx_id
                != "0000000000000000000000000000000000000000000000000000000000000000"
            ):
                # input is spending a previous output. Link it here
                previous_transaction, created = Transaction.objects.get_or_create(
                    tx_id=prev_tx_id
                )

                if created:
                    logger.error(
                        "tx {} not found for previous output to {}".format(
                            prev_tx_id[:8], tx_input
                        )
                    )
                    self.send_for_repair()

                previous_output, _ = TxOutput.objects.get_or_create(
                    transaction=previous_transaction, index=vin.get("vout"),
                )

                # check if a different input already spends this output
                try:
                    existing_t_in = TxInput.objects.get(previous_output=previous_output)
                    existing_t_in.previous_output = None
                    existing_t_in.save()
                except TxInput.DoesNotExist:
                    pass

                tx_input.previous_output = previous_output
                tx_input.save()

    def parse_output(self, vout):
        script_pubkey = vout.get("scriptPubKey", {})

        tx_output, _ = TxOutput.objects.get_or_create(
            transaction_id=self.id, index=vout.get("n"),
        )

        tx_output.value = convert_to_satoshis(vout.get("value", 0.0))
        tx_output.script_pub_key_asm = script_pubkey.get("asm", "")
        tx_output.script_pub_key_hex = script_pubkey.get("hex", "")
        tx_output.script_pub_key_type = script_pubkey.get("type", "")
        tx_output.script_pub_key_req_sig = script_pubkey.get("reqSigs", "")
        tx_output.save()

        # attach the address to the output
        for addr in script_pubkey.get("addresses", []):
            address, _ = Address.objects.get_or_create(address=addr)
            tx_output.address = address
            tx_output.save()

        # parse park outputs
        if tx_output.script_pub_key_type == "park":
            park_data = script_pubkey.get("park", {})
            tx_output.park_duration = park_data.get("duration")
            tx_output.save()

            # attach address objects to the tx_output
            address, _ = Address.objects.get_or_create(
                address=park_data.get("unparkaddress")
            )
            tx_output.address = address
            tx_output.save()

    def parse_rpc_tx(self, rpc_tx):
        logger.info("parsing tx {}".format(self))

        # get and save the block
        from blocks.models import Block

        block, created = Block.objects.get_or_create(hash=rpc_tx.get("blockhash"))

        if created:
            block.send_for_repair()

        self.block = block

        # save version, time and lock_time
        self.version = rpc_tx.get("version")
        tx_time = rpc_tx.get("time")

        if tx_time:
            self.time = make_aware(datetime.fromtimestamp(int(tx_time)))
        else:
            self.time = None

        self.lock_time = rpc_tx.get("locktime", 0)

        # get the chain and coin
        try:
            chain = Chain.objects.get(schema_name=connection.schema_name)
            coin = Coin.objects.get(chain=chain, unit_code=rpc_tx.get("unit"))
        except Chain.DoesNotExist:
            logger.error(f"No chain found matching {connection.schema_name}")
            coin = None
        except Coin.DoesNotExist:
            logger.info(
                f"No coin matching {rpc_tx.get('unit')} found in chain {connection.schema_name}"
            )
            coin = None

        self.coin = coin
        self.save()

        # for each input in the transaction, save a TxInput
        logger.info("Adding Inputs")
        vin_index = 0

        for vin in rpc_tx.get("vin", []):
            self.parse_input(vin, vin_index)
            vin_index += 1

        # save a TXOutput for each output in the Transaction
        logger.info("Adding outputs")

        for vout in rpc_tx.get("vout", []):
            self.parse_output(vout)

        self.save()
        logger.info("saved tx {}".format(self))
        return

    def validate(self):
        logger.info(f"Validating transaction {self}")

        if self.block:
            if self.block.height == 0:
                self.is_valid = True
                self.validity_errors = None
                self.save()
                return

        validation_errors = []
        check_header = True

        if self.index < 0:
            validation_errors.append("incorrect index")

        for attribute in ["self.version", "self.time", "self.index", "self.lock_time"]:
            if eval(attribute) is None:
                check_header = False

        if check_header:
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
                        codecs.decode(
                            tx_input.previous_output.transaction.tx_id, "hex"
                        )[::-1]
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
                validation_errors.append("incorrect hash")
        else:
            validation_errors.append(f"missing header attribute")

        # check for a block
        if not self.block:
            validation_errors.append("no block")

        # check the outputs for addresses
        for tx_out in self.outputs.all():
            if tx_out.script_pub_key_type in ["pubkey", "pubkeyhash", "park"]:
                if not tx_out.address:
                    validation_errors.append("output has no address")

            if tx_out.script_pub_key_type == "park":
                if not tx_out.park_duration:
                    validation_errors.append("park output has no duration")

        # check the inputs, previous outputs for addresses
        for tx_in in self.inputs.all():
            if tx_in.previous_output:
                if not tx_in.previous_output.address:
                    validation_errors.append("address missing from previous output")

                if tx_in.previous_output.value == 0:
                    validation_errors.append("previous output value is 0")

                if tx_in.previous_output.transaction.block is None:
                    validation_errors.append("previous output block is Missing")
                else:
                    if tx_in.previous_output.transaction.block.height is None:
                        validation_errors.append("previous output block height is None")

        # check for unit/coin
        if not self.coin:
            validation_errors.append("no associated coin")

        if validation_errors:
            logger.warning(f"Found validation errors: {', '.join(validation_errors)}")
            logger.info(f"Setting {self}.is_valid to False")
            self.is_valid = False
            self.validity_errors = list(set(validation_errors))
            self.save()
        else:
            self.is_valid = True
            self.validity_errors = None
            self.save()

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


class TxOutput(models.Model):
    transaction = models.ForeignKey(
        "Transaction",
        related_name="outputs",
        related_query_name="output",
        on_delete=models.CASCADE,
    )
    value = models.BigIntegerField(default=0)
    index = models.IntegerField(db_index=True)
    script_pub_key_asm = models.TextField(blank=True, default="",)
    script_pub_key_hex = models.TextField(blank=True, default="",)
    script_pub_key_type = models.TextField(blank=True, default="",)
    script_pub_key_req_sig = models.TextField(blank=True, default="",)
    address = models.ForeignKey(
        "Address",
        related_name="outputs",
        related_query_name="output_address",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    park_duration = models.BigIntegerField(blank=True, null=True,)

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


class TxInput(models.Model):
    """
    A transaction input.
    Belongs to a single transaction
    """

    transaction = models.ForeignKey(
        "Transaction",
        related_name="inputs",
        related_query_name="input",
        on_delete=models.CASCADE,
    )
    index = models.BigIntegerField(db_index=True)
    previous_output = models.OneToOneField(
        "TxOutput",
        blank=True,
        null=True,
        related_name="input",
        on_delete=models.SET_NULL,
    )
    coin_base = models.CharField(max_length=610, blank=True,)
    sequence = models.BigIntegerField(blank=True, default=4294967295,)
    script_sig_asm = models.TextField(blank=True, default="",)
    script_sig_hex = models.TextField(blank=True, default="",)

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


class Address(models.Model):
    address = models.CharField(max_length=610, unique=True, db_index=True,)

    # Addresses that are network owned are not counted in the
    # 'Circulating Currency' calculation
    network_owned = models.BooleanField(default=False)
    coin = models.ForeignKey(Coin, blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.address

    @property
    def class_type(self):
        return "Address"

    @property
    def balance(self):
        balance = self.outputs.filter(
            input__isnull=True,
            transaction__block__isnull=False,
            transaction__block__height__isnull=False,
        ).aggregate(Sum("value"))

        return balance["value__sum"] if balance["value__sum"] else 0

    def transactions(self):
        inputs = TxInput.objects.values_list("transaction", flat=True).filter(
            previous_output__address=self,
            transaction__block__isnull=False,
            transaction__block__height__isnull=False,
        )
        outputs = TxOutput.objects.values_list("transaction", flat=True).filter(
            address=self,
            transaction__block__isnull=False,
            transaction__block__height__isnull=False,
        )
        tx_ids = [tx for tx in inputs] + [tx for tx in outputs]

        return Transaction.objects.filter(id__in=tx_ids).order_by("-time")


class WatchAddress(models.Model):
    address = models.ForeignKey(
        "Address",
        related_name="watch_addresses",
        related_query_name="watch_address",
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(max_digits=20, decimal_places=6)
    call_back = models.URLField(max_length=610,)
    complete = models.BooleanField(default=False,)
