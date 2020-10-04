import codecs
import hashlib
import logging
import time
from datetime import datetime
from decimal import Decimal


from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.cache import cache
from django.db import connection, models
from django.db.models import Max, Sum
from django.db.utils import IntegrityError
from django.utils.timezone import make_aware

from .network import ActiveParkRate, Orphan
from .transaction import Transaction, TxInput, TxOutput, Address
from .votes import CustodianVote, FeesVote, MotionVote, ParkRate, ParkRateVote
from daio.celery import app

from daio.models import Chain, Coin

logger = logging.getLogger(__name__)


class Block(models.Model):
    """
    Object definition of a block
    """

    hash = models.CharField(max_length=610, unique=True, db_index=True,)
    size = models.BigIntegerField(blank=True, null=True,)
    height = models.BigIntegerField(unique=True, blank=True, null=True, db_index=True,)
    version = models.BigIntegerField(blank=True, null=True,)
    merkle_root = models.CharField(max_length=610, blank=True, null=True,)
    time = models.DateTimeField(blank=True, null=True, db_index=True)
    nonce = models.BigIntegerField(blank=True, null=True,)
    bits = models.CharField(max_length=610, blank=True, null=True,)
    difficulty = models.FloatField(blank=True, null=True,)
    mint = models.FloatField(blank=True, null=True,)
    previous_block = models.ForeignKey(
        "Block",
        related_name="previous",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    next_block = models.ForeignKey(
        "Block", related_name="next", blank=True, null=True, on_delete=models.SET_NULL,
    )
    flags = models.CharField(max_length=610, blank=True, null=True,)
    proof_hash = models.CharField(max_length=610, blank=True, null=True,)
    entropy_bit = models.BigIntegerField(blank=True, null=True,)
    modifier = models.CharField(max_length=610, blank=True, null=True,)
    modifier_checksum = models.CharField(max_length=610, blank=True, null=True,)
    coinage_destroyed = models.BigIntegerField(blank=True, null=True,)
    amount_parked = JSONField(default=dict)
    vote = JSONField(default=dict, blank=True, null=True)
    park_rates = JSONField(default=list, blank=True, null=True)
    is_valid = models.BooleanField(default=False)
    validity_errors = ArrayField(
        base_field=models.CharField(max_length=150), blank=True, null=True
    )

    def __str__(self):
        return "{}:{}".format(self.height, self.hash[:8])

    @property
    def class_type(self):
        return "Block"

    def send_for_repair(self):
        app.send_task(
            "blocks.tasks.blocks.validate_block",
            kwargs={"block_hash": self.hash},
            queue="high_priority",
        )

    def serialize(self):
        serialized_block = None
        self.validate()

        if self.is_valid:
            serialized_block = cache.get(
                "{}_{}".format(connection.tenant.schema_name, self.hash)
            )
        else:
            self.send_for_repair()

        if serialized_block is None:
            serialized_block = {
                "hash": self.hash,
                "height": self.height,
                "size": self.size,
                "version": self.version,
                "merkleroot": self.merkle_root,
                "time": (
                    datetime.strftime(self.time, "%Y-%m-%d %H:%M:%S %Z")
                    if self.time
                    else None
                ),
                "nonce": self.nonce,
                "bits": self.bits,
                "difficulty": self.difficulty,
                "mint": self.mint,
                "flags": self.flags,
                "proofhash": self.proof_hash,
                "entropybit": self.entropy_bit,
                "modifier": self.modifier,
                "modifierchecksum": self.modifier_checksum,
                "coinagedestroyed": self.coinage_destroyed,
                "previousblockhash": (
                    self.previous_block.hash if self.previous_block else None
                ),
                "nextblockhash": (self.next_block.hash if self.next_block else None),
                "valid": self.is_valid,
                "number_of_transactions": self.transactions.all().count(),
                "solved_by": self.solved_by if self.solved_by else "",
            }

            self.validate()

            if self.is_valid:
                cache.set(
                    "{}_{}".format(connection.tenant.schema_name, self.hash),
                    serialized_block,
                )

        return serialized_block

    def parse_rpc_block(self, rpc_block):
        # check if there is a different block at this height
        try:
            existing_height_block = Block.objects.get(height=self.height)
        except Block.DoesNotExist:
            existing_height_block = self
        except Block.MultipleObjectsReturned:
            # self.height is likely None
            existing_height_block = self

        if existing_height_block != self:
            logger.warning(f"Found existing block {existing_height_block}.")
            logger.info("Setting height to None and removing from chain")
            existing_height_block.height = None
            existing_height_block.previous_block = None
            existing_height_block.next_block = None
            existing_height_block.save()

        # we can safely set this blocks height now
        self.height = rpc_block.get("height")
        logger.info(f"parsing block {self}")
        # parse the json and apply to the block we just fetched
        self.size = rpc_block.get("size")
        self.version = rpc_block.get("version")
        self.merkle_root = rpc_block.get("merkleroot")
        block_time = rpc_block.get("time")

        if block_time:
            self.time = make_aware(
                datetime.strptime(block_time, "%Y-%m-%d %H:%M:%S %Z")
            )

        self.nonce = rpc_block.get("nonce")
        self.bits = rpc_block.get("bits")
        self.difficulty = rpc_block.get("difficulty")
        self.mint = rpc_block.get("mint")
        self.flags = rpc_block.get("flags")
        self.proof_hash = rpc_block.get("proofhash")
        self.entropy_bit = rpc_block.get("entropybit")
        self.modifier = rpc_block.get("modifier")
        self.modifier_checksum = rpc_block.get("modifierchecksum")
        self.coinage_destroyed = rpc_block.get("coinagedestroyed")
        self.vote = rpc_block.get("vote")
        self.park_rates = rpc_block.get("parkrate")

        # using the previousblockhash, get the block object to connect
        prev_block_hash = rpc_block.get("previousblockhash")

        # genesis block has no previous block
        if prev_block_hash:
            previous_block, _ = Block.objects.get_or_create(hash=prev_block_hash)
            self.previous_block = previous_block
            previous_block.next_block = self
            previous_block.save()

        # do the same for the next block
        next_block_hash = rpc_block.get("nextblockhash")
        if next_block_hash:
            # top block has no next block yet
            next_block, created = Block.objects.get_or_create(hash=next_block_hash)
            self.next_block = next_block
            next_block.previous_block = self
            next_block.save()

        self.save()

        # now we do the transactions
        self.parse_rpc_transactions(rpc_block.get("tx", []))

        # save the votes too
        self.parse_rpc_votes(rpc_block.get("vote", {}))

        # save active park rates
        self.parse_rpc_parkrates(rpc_block.get("parkrates", []))

        logger.info("saved block {}".format(self))

    def parse_rpc_transactions(self, txs):
        logger.info(f"Parsing rpc transactions for block {self}")

        tx_index = 0

        for rpc_tx in txs:
            tx, _ = Transaction.objects.get_or_create(tx_id=rpc_tx.get("txid"))

            tx.block = self
            tx.index = tx_index
            tx.version = rpc_tx.get("version")
            tx.lock_time = rpc_tx.get("lock_time")

            tx.save()

            input_index = 0

            for rpc_input in rpc_tx.get("vin", []):
                tx.parse_input(rpc_input, input_index)
                input_index += 1

            for rpc_output in rpc_tx.get("vout", []):
                tx.parse_output(rpc_output)

            tx.save()

    def parse_rpc_votes(self, votes):
        logger.info(f"Parsing rpc votes for block {self}")
        # custodian votes
        for custodian_vote in votes.get("custodians", []):
            custodian_address = custodian_vote.get("address")

            if not custodian_address:
                continue

            address, _ = Address.objects.get_or_create(address=custodian_address)
            amount = "{:.8f}".format(custodian_vote.get("amount"))

            if amount is None:
                logger.error("Got custodian vote amount = None parsing {}".format(self))
                continue

            try:
                CustodianVote.objects.get_or_create(
                    block=self, address=address, amount=Decimal(amount)
                )
            except (CustodianVote.DoesNotExist, IntegrityError) as e:
                logger.warning(e)
                continue

        # motion votes
        for motion_vote in votes.get("motions", []):
            try:
                motion_object, _ = MotionVote.objects.get_or_create(
                    block=self, hash=motion_vote
                )
            except (MotionVote.DoesNotExist, IntegrityError) as e:
                logger.warning(e)
                continue

            # calculate block percentage
            motion_votes = MotionVote.objects.filter(
                block__height__gte=max(self.height - 10000, 0),
                block__height__lte=self.height,
                hash=motion_vote,
            )

            motion_object.blocks_percentage = (motion_votes.count() / 10000) * 100

            # calculate the ShareDays Destroyed percentage
            total_sdd = Block.objects.filter(
                height__gte=max(self.height - 10000, 0), height__lte=self.height
            ).aggregate(Sum("coinage_destroyed"))["coinage_destroyed__sum"]

            voted_sdd = motion_votes.aggregate(Sum("block__coinage_destroyed"))[
                "block__coinage_destroyed__sum"
            ]

            motion_object.sdd_percentage = (voted_sdd / total_sdd) * 100
            motion_object.save()

        # fees votes
        fee_votes = votes.get("fees", {})
        for fee_vote in fee_votes:
            try:
                coin = Coin.objects.get(
                    chain=Chain.objects.get(schema_name=connection.schema_name),
                    unit_code=fee_vote,
                )
            except Coin.DoesNotExist:
                continue

            try:
                FeesVote.objects.get_or_create(
                    block=self, coin=coin, fee=fee_votes[fee_vote]
                )
            except (FeesVote.DoesNotExist, IntegrityError) as e:
                logger.warning(e)
                continue

        # park rate votes
        for park_rate_vote in votes.get("parkrates", []):
            try:
                coin = Coin.objects.get(
                    chain=Chain.objects.get(schema_name=connection.schema_name),
                    unit_code=park_rate_vote.get("unit"),
                )
            except Coin.DoesNotExist:
                continue

            try:
                vote, _ = ParkRateVote.objects.get_or_create(block=self, coin=coin)
            except (ParkRateVote.DoesNotExist, IntegrityError) as e:
                logger.warning(e)
                continue

            for rate in park_rate_vote.get("rates", []):
                blocks = rate.get("blocks")

                if blocks is None:
                    logger.error(
                        "Got blocks = None when parsing Park Rate Votes for {}".format(
                            self
                        )
                    )

                this_rate = rate.get("rate")

                if this_rate is None:
                    logger.error(
                        "Got rate = None when parsing Park Rate Votes for {}".format(
                            self
                        )
                    )
                try:
                    park_rate, _ = ParkRate.objects.get_or_create(
                        blocks=blocks, rate=this_rate
                    )
                except (ParkRate.DoesNotExist, IntegrityError) as e:
                    logger.warning(e)
                    continue

                try:
                    vote.rates.add(park_rate)
                except IntegrityError as e:
                    logger.warning(e)

    def parse_rpc_parkrates(self, rates):
        logger.info(f"Parsing rpc park rates for block {self}")
        for park_rate in rates:
            try:
                coin = Coin.objects.get(
                    chain=Chain.objects.get(schema_name=connection.schema_name),
                    unit_code=park_rate.get("unit"),
                )
            except Coin.DoesNotExist:
                continue

            try:
                active_rate, _ = ActiveParkRate.objects.get_or_create(
                    block=self, coin=coin
                )
            except (ActiveParkRate.DoesNotExist, IntegrityError) as e:
                logger.warning(e)
                continue

            for rate in park_rate.get("rates", []):
                try:
                    park_rate, _ = ParkRate.objects.get_or_create(
                        blocks=rate.get("blocks", 0), rate=rate.get("rate")
                    )
                except (ParkRate.DoesNotExist, IntegrityError) as e:
                    logger.warning(e)
                    continue

                try:
                    active_rate.rates.add(park_rate)
                except IntegrityError as e:
                    logger.warning(e)

    def validate(self):
        logger.info(f"Validating block {self}")

        if self.height == 0:
            self.is_valid = True
            self.validity_errors = None
            self.save()
            return

        validation_errors = []
        check_header = True

        # first check the header attributes
        for attribute in [
            "self.height",
            "self.version",
            "self.previous_block",
            "self.merkle_root",
            "self.time",
            "self.bits",
            "self.nonce",
        ]:
            if eval(attribute) is None:
                check_header = False

        # check if height is None
        if self.height is None:
            validation_errors.append("height is None")
        else:
            top_height = Block.objects.all().aggregate(Max("height"))

            if (top_height["height__max"] > self.height) and not self.next_block:
                validation_errors.append("missing next block")

        # calculate the header in bytes (little endian)
        if check_header:
            header_bytes = (
                self.version.to_bytes(4, "little")
                + codecs.decode(self.previous_block.hash, "hex")[::-1]
                + codecs.decode(self.merkle_root, "hex")[::-1]
                + int(time.mktime(self.time.timetuple())).to_bytes(4, "little")
                + codecs.decode(self.bits, "hex")[::-1]
                + self.nonce.to_bytes(4, "little")
            )

            # hash the header and fail if it doesn't match the one on record
            header_hash = hashlib.sha256(hashlib.sha256(header_bytes).digest()).digest()
            calc_hash = codecs.encode(header_hash[::-1], "hex")

            if str.encode(self.hash) != calc_hash:
                validation_errors.append("incorrect block hash")
        else:
            validation_errors.append(f"missing header attribute")

        # check the previous block
        if not self.previous_block:
            validation_errors.append("no previous block")
        else:
            if not self.previous_block.hash:
                validation_errors.append("no previous block hash")
            # check that previous block height has height and is this height - 1
            if self.previous_block.height is None:
                validation_errors.append("Previous block height is None")
            else:
                if self.height:
                    if self.previous_block.height != (self.height - 1):
                        validation_errors.append("incorrect previous height")

                if self.height > 2:
                    if self.previous_block.previous_block is None:
                        validation_errors.append("previous block has no previous block")
                    else:
                        if self.previous_block.previous_block.height is None:
                            validation_errors.append(
                                "previous blocks previous block height is None"
                            )

            # check the previous block next block is this block
            if self.previous_block.next_block != self:
                validation_errors.append("previous block does not point to this block")

        # check the next block
        if self.next_block:
            if self.height:
                if self.next_block.height != (self.height + 1):
                    validation_errors.append("incorrect next height")

            # check the next block has this block as it's previous block
            if self.next_block.previous_block != self:
                validation_errors.append("next block does not lead on from this block")

        # calculate merkle root of transactions
        transactions = list(
            self.transactions.all().order_by("index").values_list("tx_id", flat=True)
        )
        merkle_root = self._calculate_merkle_root(transactions)

        if isinstance(merkle_root, bytes):
            merkle_root = merkle_root.decode()

        if merkle_root != self.merkle_root:
            validation_errors.append("merkle root incorrect")

        # check the indexes on transactions are incremental
        for x in range(self.transactions.all().count()):
            if self.transactions.filter(index=x).count() != 1:
                validation_errors.append("incorrect tx indexing")

        # check that the serialized votes match the saved raw votes
        # custodian votes
        custodians = []

        for custodian_vote in self.custodianvote_set.all():
            custodians.append(
                {
                    "address": custodian_vote.address.address,
                    "amount": float(custodian_vote.amount),
                }
            )

        if sorted(custodians, key=lambda c: c["address"]) != sorted(
            self.vote.get("custodians", []), key=lambda c: c["address"]
        ):
            validation_errors.append("custodian votes do not match")

        # park rate votes
        park_rate_votes = []

        for park_rate_coin in self.parkratevote_set.all().distinct("coin"):
            coin_park_rates = {"unit": park_rate_coin.coin.unit_code, "rates": []}
            for park_rate_vote in self.parkratevote_set.filter(
                coin=park_rate_coin.coin
            ):
                for rate in park_rate_vote.rates.all():
                    coin_park_rates["rates"].append(
                        {"blocks": rate.blocks, "rate": rate.rate}
                    )
                park_rate_votes.append(coin_park_rates)

        for rate_vote in self.vote.get("parkrates", []):
            raw_rate_vote = next(
                (r for r in park_rate_votes if r["unit"] == rate_vote["unit"]), {}
            )
            if sorted(rate_vote.get("rates", []), key=lambda r: r["blocks"]) != sorted(
                raw_rate_vote.get("rates", []), key=lambda r: r["blocks"]
            ):
                validation_errors.append("park rate votes do not match")

        # motion votes
        motions = []

        for motion in self.motionvote_set.all():
            motions.append(motion.hash)

        if sorted(set(motions)) != sorted(set(self.vote.get("motions", []))):
            validation_errors.append("motion votes do not match")

        # fee votes
        fees = {}

        for fee_vote in self.feesvote_set.all():
            fees[fee_vote.coin.unit_code] = fee_vote.fee

        if sorted(fees) != sorted(self.vote.get("fees", {})):
            validation_errors.append("fee votes do not match")

        # check active park rates against raw
        active_park_rates = []

        for apr in self.activeparkrate_set.all().distinct("coin"):
            coin_park_rates = {"unit": apr.coin.unit_code, "rates": []}

            for park_rate in self.activeparkrate_set.filter(coin=apr.coin):
                for rate in park_rate.rates.all():
                    coin_park_rates["rates"].append(
                        {"blocks": rate.blocks, "rate": rate.rate}
                    )
                active_park_rates.append(coin_park_rates)

        raw_park_rates = self.park_rates if self.park_rates is not None else []

        for park_rate in raw_park_rates:
            raw_rate = next(
                (r for r in active_park_rates if r["unit"] == park_rate["unit"]), {}
            )
            if sorted(park_rate.get("rates", []), key=lambda r: r["blocks"]) != sorted(
                raw_rate.get("rates", []), key=lambda r: r["blocks"]
            ):
                validation_errors.append("active park rates do not match")

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

    def _calculate_merkle_root(self, hash_list):
        def merkle_hash(a, b):
            # Reverse inputs before and after hashing
            # due to big-endian / little-endian nonsense
            a1 = codecs.decode(a, "hex")[::-1]
            b1 = codecs.decode(b, "hex")[::-1]
            h = hashlib.sha256(hashlib.sha256(a1 + b1).digest()).digest()
            return codecs.encode(h[::-1], "hex")

        if not hash_list:
            return "".encode()
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
        index = 1

        if self.flags == "proof-of-work":
            index = 0

        for tx in self.transactions.all():
            if tx.index == index:
                for tx_out in tx.outputs.all():
                    if tx_out.index == index:
                        if not tx_out.address:
                            return ""
                        return tx_out.address.address
        return ""

    @property
    def solved_by_address(self):
        index = 1

        if self.flags == "proof-of-work":
            index = 0

        for tx in self.transactions.all():
            if tx.index == index:
                for tx_out in tx.outputs.all():
                    if tx_out.index == index:
                        if not tx_out.address:
                            return None
                        return tx_out.address
        return None

    @property
    def totals_transacted(self):
        chain = connection.tenant
        totals = []
        for coin in chain.coins.all():
            coin_total = {"name": coin.code, "value": 0}
            for tx in self.transactions.all():
                if tx.coin != coin:
                    continue
                coin_total["value"] += tx.balance
            totals.append(coin_total)
        return totals

    @property
    def outputs(self):
        outputs = {"spent": {}, "unspent": {}}
        for tx in self.transactions.all():
            if tx.index < 2:
                continue
            for tx_output in tx.outputs.all():
                try:
                    if not tx_output.input.transaction.block:
                        try:
                            tx_output.input.transaction.delete()
                            continue
                        except IntegrityError:
                            continue
                    if not tx_output.input.transaction.block.height:
                        continue
                    # if this works the output is spent
                    if tx_output.input.transaction.block not in outputs["spent"]:
                        outputs["spent"][tx_output.input.transaction.block] = 0
                    outputs["spent"][
                        tx_output.input.transaction.block
                    ] += tx_output.display_value  # noqa
                except TxInput.DoesNotExist:
                    # accessing output.input fails if output is unspent
                    if not tx_output.address:
                        continue
                    if tx_output.address not in outputs["unspent"]:
                        outputs["unspent"][tx_output.address] = 0
                    outputs["unspent"][tx_output.address] += tx_output.display_value
        return outputs

    def calculate_amount_parked(self):
        chain = connection.tenant
        parked_totals = {}

        for coin in chain.coins.all():
            unparked_outputs = (
                TxOutput.objects.filter(
                    script_pub_key_type="park",
                    transaction__block__height__lte=self.height,
                    input__transaction__block__height__gt=self.height,
                    transaction__coin__unit_code=coin.unit_code,
                )
                .exclude(transaction__block__isnull=True)
                .aggregate(Sum("value"))
            )

            unparked_value = (
                unparked_outputs["value__sum"]
                if unparked_outputs["value__sum"] is not None
                else 0
            )

            still_parked_outputs = (
                TxOutput.objects.filter(
                    script_pub_key_type="park",
                    transaction__block__height__lte=self.height,
                    input__isnull=True,
                    transaction__coin__unit_code=coin.unit_code,
                )
                .exclude(transaction__block__isnull=True)
                .aggregate(Sum("value"))
            )

            still_parked_value = (
                still_parked_outputs["value__sum"]
                if still_parked_outputs["value__sum"] is not None
                else 0
            )

            parked_totals[coin.unit_code] = (
                unparked_value + still_parked_value
            ) / coin.decimal_places

        return parked_totals
