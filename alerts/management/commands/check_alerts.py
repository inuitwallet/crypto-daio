from django.core.management import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        pass
        # get all alerts
        # check their conditions
        # send notification appropriately
