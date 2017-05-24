import json
import logging

from channels import Group
from tenant_schemas.utils import schema_context

from blocks.models import Info
from daio.models import Chain

logger = logging.getLogger(__name__)


def update_info(info_id, value):
    Group('update_info').send(
        {
            'text': json.dumps(
                {
                    'message_type': 'update_info',
                    'id': info_id,
                    'value': value
                }
            )
        }
    )


def display_info(message):
    """
    get the latest info objects and send them for display on the front end
    :param message: 
    :return: 
    """
    chain = Chain.objects.get(schema_name=str(message.get('chain')))
    with schema_context(message.get('chain')):
        max_height = 0
        connections = 0

        for coin in chain.coins.all():
            info = Info.objects.filter(unit=coin.unit_code).order_by('-max_height').first()
            update_info('{}-supply'.format(coin.code), str(info.money_supply))
            update_info('{}-parked'.format(coin.code), str(info.total_parked))
            update_info('{}-fee'.format(coin.code), str(info.pay_tx_fee))

            max_height = str(info.max_height)
            connections = str(info.connections)

        update_info('connections', connections)
        update_info('height', max_height)

