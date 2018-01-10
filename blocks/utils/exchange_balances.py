import requests


def get_exchange_balances(coin_object):
    exchange_balances = []

    for exchange_balance in coin_object.exchangebalance_set.all():
        r = requests.get(
            url=exchange_balance.api_url,
            headers={
                'Authorization': 'Bearer {}'.format(
                    exchange_balance.api_token
                ),
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )

        try:
            query_data = r.json()
        except ValueError as e:
            print(
                'Invalid response when querying data for {}: {}'.format(
                    exchange_balance.api_url,
                    e
                )
            )
            continue

        time = 0
        exchange_balance = {'exchange': exchange_balance.exchange, 'balance': 0}

        for data_point in query_data[0].get('datapoints', []):
            if int(data_point[1]) > time:
                time = data_point[1]
                if data_point[0]:
                    exchange_balance['balance'] = data_point[0]

        exchange_balances.append(exchange_balance)

    return exchange_balances
