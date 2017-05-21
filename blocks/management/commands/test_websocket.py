import json
import logging
from time import sleep

from django.core.management import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from channels import Group

from blocks.models import Block

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        Get the latest info from the coin daemon and  
        """
        for block in Block.objects.all().order_by('-height')[:15]:
            Group('latest_blocks_list').send(
                {
                    'text': json.dumps(
                        {
                            'block_height': block.height,
                            'block_html': render_to_string(
                                'explorer/fragments/block.html',
                                {
                                    'block': block
                                }
                            )
                        }
                    )
                }
            )
