import json
import logging

from channels import Group
from tenant_schemas.utils import schema_context

from blocks.models import Info
from daio.models import Chain

logger = logging.getLogger(__name__)


def update_info(info_id, value, schema):
    Group('{}_update_info'.format(schema)).send(
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
    schema = str(message.get('chain'))
    chain = Chain.objects.get(schema_name=schema)
    with schema_context(schema):
        max_height = 0
        connections = 0

        for coin in chain.coins.all():
            info = Info.objects.filter(
                unit=coin.unit_code
            ).order_by(
                '-max_height'
            ).first()
            if not info:
                continue
            update_info('{}-supply'.format(coin.code), str(info.money_supply), schema)
            update_info('{}-parked'.format(coin.code), str(info.total_parked), schema)
            update_info('{}-fee'.format(coin.code), str(info.pay_tx_fee), schema)

            max_height = str(info.max_height)
            connections = str(info.connections)

        update_info('connections', connections, schema)
        update_info('height', max_height, schema)

