from django.db import connection
from django.views.generic import ListView

from charts.models import CurrencyValue, Trade


class TradeValueTable(ListView):
    model = Trade
    ordering = '-date_time'
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super(TradeValueTable, self).get_context_data(**kwargs)
        new_object_list = []
        for trade in context['object_list']:
            if not trade.date_time:
                continue

            trade.adjusted_amount = trade.amount
            if trade.pair.quote_currency.get_usd_value:
                closest_value = CurrencyValue.objects.get_closest_to(
                    trade.pair.quote_currency,
                    trade.date_time
                ).usd_value
                trade.quote_price = closest_value
                if trade.amount and closest_value:
                    trade.adjusted_amount = trade.amount * closest_value

            trade.adjusted_rate = trade.rate
            trade.adjusted_total = trade.total
            if trade.pair.base_currency.get_usd_value:
                closest_value = CurrencyValue.objects.get_closest_to(
                    trade.pair.base_currency,
                    trade.date_time
                ).usd_value
                trade.base_price = closest_value
                if trade.rate and closest_value:
                    trade.adjusted_rate = trade.rate * closest_value
                if trade.total and closest_value:
                    trade.adjusted_total = trade.total * closest_value

            new_object_list.append(trade)

        context['object_list'] = new_object_list
        context['chain'] = connection.tenant
        return context
