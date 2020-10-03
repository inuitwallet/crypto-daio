from django.contrib import messages
from django.db import connection
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from blocks.tasks import repair_transaction, repair_block
from blocks.models import ActiveParkRate, Block, Transaction


class LatestBlocksList(ListView):
    model = Block
    template_name = "explorer/latest_blocks_list.html"

    def get_queryset(self):
        blocks = Block.objects.exclude(height=None).order_by("-height")[:50]

        for block in blocks:
            repair_block.apply_async(
                kwargs={"block_hash": block.hash}, queue="high_priority"
            )

        return blocks

    def get_context_data(self, **kwargs):
        context = super(LatestBlocksList, self).get_context_data(**kwargs)
        context["chain"] = connection.tenant
        context["active_park_rates"] = []

        for coin in connection.tenant.coins.all():
            park_rate = ActiveParkRate.objects.filter(
                block=Block.objects.exclude(height=None).order_by("-height").first(),
                coin=coin,
            ).first()

            if park_rate:
                context["active_park_rates"].append(park_rate)

        return context


class BlockDetailView(View):
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(BlockDetailView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def get(request, block_height):
        block = get_object_or_404(Block, height=block_height)
        repair_block.apply_async(
            kwargs={"block_hash": block.hash}, queue="high_priority"
        )

        for tx in block.transactions.all():
            repair_transaction.apply_async(
                kwargs={"tx_id": tx.tx_id}, queue="high_priority"
            )

        return render(
            request,
            "explorer/block_detail.html",
            {"object": block, "chain": connection.tenant},
        )

    @staticmethod
    def post(request, block_height):
        # validate the given transaction and return the same page
        if "tx_pk" in request.POST:
            # attempt to get the transaction if it exists
            try:
                tx = Transaction.objects.get(pk=request.POST["tx_pk"])
                # save the tx to start validation
                tx.save()
            except Transaction.DoesNotExist:
                pass
        return render(
            request,
            "explorer/block_detail.html",
            {
                "object": get_object_or_404(Block, height=block_height),
                "chain": connection.tenant,
            },
        )


class AllBlocks(ListView):
    model = Block
    paginate_by = 20
    template_name = "explorer/all_blocks_list.html"

    def get(self, request, *args, **kwargs):
        self.kwargs["GET"] = request.GET
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        print("getting queryset")
        blocks = Block.objects.exclude(height=None).order_by("-height")

        print(f"Got blocks: {blocks}")
        if "start-from" in self.kwargs["GET"]:
            print("calculating start from")
            start_from = self.kwargs["GET"]["start-from"]

            if start_from:
                try:
                    start_height = int(start_from)
                    blocks = blocks.filter(height__lte=start_height)
                    messages.add_message(
                        self.request,
                        messages.SUCCESS,
                        f"Showing blocks from {start_height}",
                    )
                except (ValueError, TypeError):
                    messages.add_message(
                        self.request, messages.ERROR, f"The search was invalid"
                    )
            else:
                messages.add_message(
                    self.request, messages.ERROR, f"The search can't be blank"
                )

        print("returning blocks")
        return blocks

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["chain"] = connection.tenant
        return context
