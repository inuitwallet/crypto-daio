from channels import Group
from channels.generic.websockets import JsonWebsocketConsumer
from tenant_schemas.utils import get_tenant_model, tenant_context

from blocks.models import Block
from blocks.consumers.angular_consumers import get_host
import logging

logger = logging.getLogger(__name__)


class LatestBlocksConsumer(JsonWebsocketConsumer):
    channel_session = True

    def connect(self, message, **kwargs):
        try:
            tenant = get_tenant_model().objects.get(
                domain_url=get_host(message.content)
            )
        except get_tenant_model().DoesNotExist:
            logger.error(
                'no tenant found for {}'.format(
                    get_host(message.content)
                )
            )
            message.reply_channel.send({"close": True})
            return

        message.channel_session['schema'] = tenant.schema_name

        super().connect(message, **kwargs)

        Group(
            '{}_latest_blocks'.format(tenant.schema_name)
        ).add(
            message.reply_channel
        )

        with tenant_context(tenant):
            latest_blocks = Block.objects.exclude(
                height__isnull=True
            ).order_by(
                '-height'
            )[:20]

            kwargs.get('multiplexer').send(
                {
                    "latest_blocks": [
                        block.serialize() for block in latest_blocks
                    ]
                }
            )

    def disconnect(self, message, **kwargs):
        if 'schema' not in message.channel_session:
            return

        Group(
            '{}_latest_blocks'.format(message.channel_session['schema'])
        ).discard(
            message.reply_channel
        )


class MoreBlocksConsumer(JsonWebsocketConsumer):
    channel_session = True

    def connect(self, message, **kwargs):
        try:
            tenant = get_tenant_model().objects.get(
                domain_url=get_host(message.content)
            )
        except get_tenant_model().DoesNotExist:
            logger.error(
                'no tenant found for {}'.format(
                    get_host(message.content)
                )
            )
            message.reply_channel.send({"close": True})
            return

        message.channel_session['tenant'] = tenant.pk
        super().connect(message, **kwargs)

    def receive(self, content, **kwargs):
        tenant_pk = self.message.channel_session.get('tenant')
        logger.info('tenant pk: {}'.format(tenant_pk))

        if tenant_pk is None:
            logger.error('TransactionConsumer tenant not in session')
            return

        try:
            tenant = get_tenant_model().objects.get(
                pk=tenant_pk
            )
        except get_tenant_model().DoesNotExist:
            return

        with tenant_context(tenant):
            more_blocks = Block.objects.exclude(
                height__isnull=True
            ).filter(
                height__lt=content.get('height')
            ).order_by(
                '-height'
            )[:20]

            kwargs.get('multiplexer').send(
                {
                    "more_blocks": [
                        block.serialize() for block in more_blocks
                    ]
                }
            )


class BlockConsumer(JsonWebsocketConsumer):
    channel_session = True

    # def connect(self, message, multiplexer, **kwargs):
    #     try:
    #         tenant = get_tenant_model().objects.get(
    #             domain_url=get_host(message.content)
    #         )
    #     except get_tenant_model().DoesNotExist:
    #         logger.error(
    #             'no tenant found for {}'.format(
    #                 get_host(message.content)
    #             )
    #         )
    #         message.reply_channel.send({"close": True})
    #         return
    #
    #     self.message.channel_session['tenant'] = tenant.pk
    #     self.message.channel_session['schema'] = tenant.schema_name
    #
    #     Group(
    #         '{}_block'.format(tenant.schema_name)
    #     ).add(
    #         message.reply_channel
    #     )
    #
    #     super().connect(message, **kwargs)

    def receive(self, content, multiplexer, **kwargs):
        logger.info(multiplexer)
        logger.info(self.message)
        tenant_pk = self.message.channel_session.get('tenant')
        logger.info('tenant pk: {}'.format(tenant_pk))

        if tenant_pk is None:
            logger.error('TransactionConsumer tenant not in session')
            logger.info(self.message.channel)
            return

        try:
            tenant = get_tenant_model().objects.get(
                pk=tenant_pk
            )
        except get_tenant_model().DoesNotExist:
            return

        with tenant_context(tenant):
            try:
                block = Block.objects.get(height=content.get('height'))
            except Block.DoesNotExist:
                return

            multiplexer.send(
                {
                    'block': block.serialize(),
                    'next_block': block.next_block.height if block.next_block else None,
                    'previous_block': block.previous_block.height if block.previous_block else None,
                }
            )

    def disconnect(self, message, multiplexer, **kwargs):
        if 'schema' not in self.message.channel_session:
            return

        Group(
            '{}_block'.format(message.channel_session['schema'])
        ).discard(
            message.reply_channel
        )


class TransactionConsumer(JsonWebsocketConsumer):
    channel_session = True

    # def connect(self, message, multiplexer, **kwargs):
    #     try:
    #         tenant = get_tenant_model().objects.get(
    #             domain_url=get_host(message.content)
    #         )
    #     except get_tenant_model().DoesNotExist:
    #         logger.error(
    #             'no tenant found for {}'.format(
    #                 get_host(message.content)
    #             )
    #         )
    #         message.reply_channel.send({"close": True})
    #         return
    #
    #     Group(
    #         '{}_transaction'.format(tenant.schema_name)
    #     ).add(
    #         message.reply_channel
    #     )
    #
    #     message.channel_session['tenant'] = tenant.pk
    #     message.channel_session['schema'] = tenant.schema_name
    #     super().connect(message, **kwargs)

    def receive(self, content, multiplexer, **kwargs):
        logger.info(multiplexer)
        tenant_pk = self.message.channel_session.get('tenant')
        logger.info('tenant pk: {}'.format(tenant_pk))

        if tenant_pk is None:
            logger.error('TransactionConsumer tenant not in session')
            logger.info(self.message.content)
            return

        try:
            tenant = get_tenant_model().objects.get(
                pk=tenant_pk
            )
        except get_tenant_model().DoesNotExist:
            return

        with tenant_context(tenant):
            try:
                block = Block.objects.get(height=int(content.get('height')))
            except Block.DoesNotExist:
                return

            multiplexer.send(
                {
                    'transactions': [
                        tx.serialize() for tx in block.transactions.all()
                    ]
                }
            )

    def disconnect(self, message, multiplexer, **kwargs):
        if 'schema' not in message.channel_session:
            return

        Group(
            '{}_transaction'.format(message.channel_session['schema'])
        ).discard(
            message.reply_channel
        )
