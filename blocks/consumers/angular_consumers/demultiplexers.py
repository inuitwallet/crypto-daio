import logging

from channels import Group
from channels.generic.websockets import WebsocketDemultiplexer
from tenant_schemas.utils import get_tenant_model

from blocks.consumers.angular_consumers import get_host
from blocks.consumers.angular_consumers.block import (BlockConsumer,
                                                      LatestBlocksConsumer,
                                                      MoreBlocksConsumer,
                                                      TransactionConsumer)

logger = logging.getLogger(__name__)


class LatestBlocksDemultiplexer(WebsocketDemultiplexer):
    consumers = {
        "latest_blocks": LatestBlocksConsumer,
        "more_blocks": MoreBlocksConsumer,
    }


class BlockDemultiplexer(WebsocketDemultiplexer):
    consumers = {
        "block": BlockConsumer,
        "transactions": TransactionConsumer,
    }

    channel_session = True

    def connect(self, message, **kwargs):
        logger.info("demulitplexer connect")
        try:
            tenant = get_tenant_model().objects.get(
                domain_url=get_host(message.content)
            )
        except get_tenant_model().DoesNotExist:
            logger.error("no tenant found for {}".format(get_host(message.content)))
            message.reply_channel.send({"close": True})
            return

        Group("{}_transaction".format(tenant.schema_name)).add(message.reply_channel)

        message.channel_session["tenant"] = tenant.pk
        message.channel_session["schema"] = tenant.schema_name
        super().connect(message, **kwargs)
