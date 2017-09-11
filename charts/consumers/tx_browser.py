import logging

logger = logging.getLogger(__name__)


def recalc_browser(message_dict, message):
    """
    {
        'stream': 'browser',
        'payload': {
            'edges': [
                'feaf79d0-762d-45b3-9598-62b3bdafd6cd',
                'cc7c99fa-b5e4-474a-9304-3dc65c54d803',
                '5017300d-f349-4835-89a4-aa152dcbf293',
                '11fe9c1e-81ce-4430-9d11-601d4d58ed4c',
                '0ebe904e-436a-4234-95d9-8dd59f6e3d3d',
                '954617f7-9b8f-4bec-aefa-3887ed592f21',
                '24f199d7-5901-4076-9946-53b4453a9dae',
                '1beed7e9-a22f-4146-8c6e-79b4d1dc98c3',
                '235e687f-8273-4723-9cb8-9b5cf7ea7e7a',
                '79841b08-93ec-479c-a5a2-a9cf6caaf5d3',
                'c6f874bb-d862-472a-888c-52c743f51fd4',
                'fad31555-79b3-4d1e-a1c2-0dad6981f47f',
                'bf574a31-5954-43f3-94ba-4949cef87a9d',
                '1dc738af-9c64-4ad2-997b-4b703c0c5ea6',
                '59f92a44-10ae-4f6e-99cd-4b2c8dd434d1'
            ],
            'nodes': [
                'SSajkovCPXwdw46nyJ7vpTDkwtRZJzyY2z'
            ],
            'host': 'nu.crypto-daio.co.uk'
        }
    }
    :param message_dict:
    :param message:
    :return:
    """
    seed_nodes = message_dict['payload'].get('seed_nodes', [])
    logger.info(seed_nodes)
    for node in seed_nodes:
        # an address has a label
        is_address = node.get('label')




