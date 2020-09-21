import json

from channels import Group
from django.core.management import BaseCommand
from django.db import connection

from blocks.models import Block


class Command(BaseCommand):
    def handle(self, *args, **options):
        latest_blocks = Block.objects.exclude(height__isnull=True).order_by("-height")[
            1:7
        ]

        Group("{}_latest_blocks".format(connection.tenant.schema_name)).send(
            {
                "text": json.dumps(
                    {
                        "stream": "latest_blocks",
                        "payload": {
                            "latest_blocks": [
                                block.serialize() for block in latest_blocks
                            ]
                        },
                    }
                )
            }
        )
