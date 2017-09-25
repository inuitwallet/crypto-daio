from django.db import models


class UserSocket(models.Model):
    reply_channel = models.CharField(
        max_length=255,
        unique=True
    )
    time_created = models.DateTimeField(
        auto_now_add=True
    )
    tx_browser_running = models.BooleanField(
        default=False
    )
    blocks = models.ManyToManyField(
        'blocks.Block'
    )

    def __str__(self):
        return '{} {}'.format(self.reply_channel, self.tx_browser_running)
