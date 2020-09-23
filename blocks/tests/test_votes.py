from tenant_schemas.test.cases import TenantTestCase

from blocks.models import ParkRate


class TestVotes(TenantTestCase):
    def test_human_readable_park_rates(self):
        # create a park rate with 1 day period and 1% APR
        rate = ParkRate.objects.create(blocks=1440, rate=1)

        self.assertEqual(rate.days, 1)
        self.assertEqual(rate.daily_percentage, 0.00273973)
        self.assertEqual(rate.overall_return, 2.73973)
