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

    @staticmethod
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

    def handle(self, *args, **options):
        """
        Get the latest info from the coin daemon and  
        """
        self.update_info('USNBT-fee', 456)
