import datetime
import json

from celery.utils.log import get_task_logger
from channels import Group, Channel
from django.core.paginator import Paginator

from django.db import connection
from django.db.models import Max
from django.template.loader import render_to_string
from django.utils.timezone import make_aware
from tenant_schemas.utils import schema_context

from blocks.models import Block, Info, Peer
from daio.celery import app
from daio.models import Coin
from .blocks import repair_block, get_block
from .transactions import repair_transaction
from blocks.utils.rpc import send_rpc

logger = get_task_logger(__name__)


@app.task
def trigger_validation(chain):
    validation.apply_async(kwargs={"chain": chain}, queue="validation")


@app.task
def validation(chain):
    with schema_context(chain):
        blocks = (
            Block.objects.exclude(height=None).filter(is_valid=False).order_by("height")
        )
        paginator = Paginator(blocks, 1000)

        for page_num in paginator.page_range:
            for block in paginator.page(page_num):

                repair_block.apply_async(
                    kwargs={"block_hash": block.hash}, queue="validation"
                )

                for tx in block.transactions.all():
                    repair_transaction.apply_async(
                        kwargs={"tx_id": tx.tx_id}, queue="validation"
                    )


@app.task
def get_latest_blocks(chain):
    with schema_context(chain):
        get_peer_info.delay(chain)
        get_info.apply(kwargs={"chain": chain})
        max_height = Info.objects.all().aggregate(Max("max_height"))["max_height__max"]
        next_height = Block.objects.all().aggregate(Max("height"))["height__max"] + 1

        while next_height <= max_height:
            logger.info(f"Getting block at height {next_height}")
            get_block.delay(next_height)
            next_height += 1

        logger.info("Refreshing Blocks on front page")
        index = 0
        top_blocks = Block.objects.exclude(height=None).order_by("-height")[:50]

        for block in top_blocks:
            Group("{}_latest_blocks_list".format(connection.schema_name)).send(
                {
                    "text": json.dumps(
                        {
                            "message_type": "update_block",
                            "index": index,
                            "block_html": render_to_string(
                                "explorer/fragments/block.html", {"block": block}
                            ),
                            "block_is_valid": block.is_valid,
                        }
                    )
                }
            )
            index += 1


@app.task
def get_info(chain):
    with schema_context(chain):
        for coin in Coin.objects.filter(chain__schema_name=chain):
            logger.info(f"getting info for coin {coin} on chain {chain}")
            rpc, message = send_rpc(
                {"method": "getinfo", "params": []},
                schema_name=connection.schema_name,
                rpc_port=coin.rpc_port,
            )

            if not rpc:
                continue

            info = Info.objects.create(
                unit=rpc["walletunit"],
                max_height=rpc["blocks"],
                money_supply=rpc["moneysupply"],
                total_parked=rpc.get("totalparked"),
                connections=rpc["connections"],
                difficulty=rpc["difficulty"],
                pay_tx_fee=rpc["paytxfee"],
            )

            logger.info(f"saved {info} for coin {coin}")

        Channel("display_info").send({"chain": connection.schema_name})


@app.task
def get_peer_info(chain):
    with schema_context(chain):
        rpc, msg = send_rpc(
            {"method": "getpeerinfo", "params": []}, schema_name=connection.schema_name,
        )

        if not rpc:
            return

        for peer_info in rpc:
            address = peer_info.get("addr")

            if not address:
                continue

            address_part = address.split(":")
            last_send = make_aware(
                datetime.datetime.fromtimestamp(peer_info.get("lastsend", 0))
            )
            last_receive = make_aware(
                datetime.datetime.fromtimestamp(peer_info.get("lastrecv", 0))
            )
            connection_time = make_aware(
                datetime.datetime.fromtimestamp(peer_info.get("conntime", 0))
            )

            peer, _ = Peer.objects.update_or_create(
                address=address_part[0],
                defaults={
                    "port": address_part[1],
                    "services": peer_info.get("services"),
                    "last_send": last_send,
                    "last_receive": last_receive,
                    "connection_time": connection_time,
                    "version": peer_info.get("version"),
                    "sub_version": peer_info.get("subver"),
                    "inbound": peer_info.get("inbound"),
                    "release_time": peer_info.get("releasetime"),
                    "height": peer_info.get("height"),
                    "ban_score": peer_info.get("banscore"),
                },
            )

            logger.info("saved peer {}".format(peer))
