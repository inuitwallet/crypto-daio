from django.db import models
from tenant_schemas.models import TenantMixin


class Chain(TenantMixin):
    auto_create_schema = True
    name = models.CharField(
        max_length=255,
        unique=True
    )
    rpc_user = models.CharField(max_length=255)
    rpc_password = models.CharField(max_length=255)
    rpc_host = models.GenericIPAddressField(default='192.168.0.1')
    rpc_port = models.PositiveIntegerField(default=1)
    logo = models.FileField(
        upload_to='logo/',
        max_length=255
    )

    def __str__(self):
        return self.name


class Coin(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    unit_code = models.CharField(max_length=255)
    chain = models.ForeignKey(Chain, related_name='coins', related_query_name='coin')
    rpc_port = models.PositiveIntegerField(default=1)
    magic_byte = models.IntegerField()
    vout_n_value = models.CharField(max_length=255, default='ffffffff')
    index = models.IntegerField(
        default=0
    )
    decimal_places = models.PositiveIntegerField(default=8)

    def __str__(self):
        return self.code

    class Meta:
        ordering = ['index']
