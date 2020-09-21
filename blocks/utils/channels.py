import logging
import time

from asgiref.base_layer import BaseChannelLayer
from channels import Channel

logger = logging.getLogger(__name__)


def send_to_channel(channel, message):
    try:
        Channel(channel).send(message)
    except BaseChannelLayer.ChannelFull:
        logger.error("Channel Full. Sleeping for a bit")
        time.sleep(600)
        return send_to_channel(channel, message)
