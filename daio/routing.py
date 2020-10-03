from channels import route

from blocks.consumers.info import display_info
from blocks.consumers.websockets import ws_connect, ws_disconnect, ws_receive

channel_routing = [
    # Info
    route("display_info", display_info),
    # Websockets
    route("websocket.connect", ws_connect),
    route("websocket.disconnect", ws_disconnect),
    route("websocket.receive", ws_receive),
]
