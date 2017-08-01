from django.db import models


class Connector(models.Model):
    provider = models.CharField(
        max_length=255,
        choices=[
            ('Discourse', 'Discourse'),
            ('Gitter', 'Gitter'),
            ('Email', 'Email')
        ]
    )
    name = models.CharField(
        max_length=255
    )
    base_url = models.URLField(
        max_length=255
    )
    api_key = models.CharField(
        max_length=255
    )
    api_user_name = models.CharField(
        max_length=255
    )
    target_channel = models.CharField(
        max_length=255
    )

    def __str__(self):
        return '{} - {}'.format(self.provider.title(), self.name)
