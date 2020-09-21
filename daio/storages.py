import os

from django.core.exceptions import SuspiciousOperation
from django.db import connection
from django.utils.encoding import force_text, smart_text
from storages.backends.s3boto3 import S3Boto3Storage
from tenant_schemas.storage import TenantStorageMixin


class DaioStorage(TenantStorageMixin, S3Boto3Storage):
    """
    Add the Tenant aware storage path to the s3boto3 storage class
    """

    def path(self, name):
        """
        Look for files in subdirectory of MEDIA_ROOT using the tenant's
        domain_url value as the specifier.
        """
        if name is None:
            name = ""
        location = connection.tenant.domain_url
        try:
            path = os.path.join(location, name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)
        return os.path.normpath(path)

    def _encode_name(self, name):
        return smart_text(self.path(name), encoding=self.file_name_charset)

    def _decode_name(self, name):
        return force_text(self.path(name), encoding=self.file_name_charset)
