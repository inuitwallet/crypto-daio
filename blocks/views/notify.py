import json

from channels import Group
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, HttpResponseNotFound
from django.template.loader import render_to_string
from django.views import View

from blocks.models import Block


class Notify(View):
    """
    Used by the coin daemon to notify of a new block
    """

    @staticmethod
    def get(request, block_hash, secret_hash):
        if secret_hash not in settings.NOTIFY_SECRET_HASHES:
            return HttpResponseNotFound()
        if len(block_hash) < 60:
            return HttpResponseNotFound()
        # block validation is tied to the save method
        Block.objects.get_or_create(hash=block_hash)

        # update top blocks on ui
        top_blocks = Block.objects.exclude(height=None).order_by("-height")[:50]
        index = 0

        for block in top_blocks:
            block.save()
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
        return HttpResponse("daio received block {}".format(block_hash))
