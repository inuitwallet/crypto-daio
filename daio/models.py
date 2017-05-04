from django.db import models
from tenant_schemas.models import TenantMixin


class Chain(TenantMixin):
    auto_create_schema = True
    name = models.CharField(
        max_length=255,
        unique=True
    )
    rcp_user = models.CharField(max_length=255)
    rpc_password = models.CharField(max_length=255)
    rpc_host = models.GenericIPAddressField()
    rpc_port = models.PositiveIntegerField()

    def __str__(self):
        return self.name


class Coin(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    unit_code = models.CharField(max_length=255)
    chain = models.ForeignKey(Chain, related_name='coins', related_query_name='coin')

    def __str__(self):
        return self.code
