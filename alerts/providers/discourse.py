import datetime

import requests


class Discourse(object):

    def __init__(self, base_url, api_key, api_username):
        self.base_url = base_url
        self.api_key = api_key
        self.api_username = api_username

    @staticmethod
    def make_headers():
        return {
            'Content-Type': 'multipart/form-data;'
        }

    def make_data(self, data):
        data['api_key'] = self.api_key
        data['api_username'] = self.api_username
        return data

    def make_request(self, endpoint, verb, data):
        response = None

        if verb.upper() not in ['GET', 'POST']:
            return False
        if verb.upper() == 'GET':
            response = requests.get(
                url='{}/{}'.format(self.base_url, endpoint),
            )
        if verb.upper() == 'POST':
            response = requests.post(
                url='{}/{}'.format(self.base_url, endpoint),
                headers=self.make_headers(),
                data=self.make_data(data)
            )

        try:
            return response.json()
        except ValueError:
            return response.text

    def send_notification(self, channel_id, message):
        self.make_request(
            'posts',
            'POST',
            {
                "topic_id": channel_id,
                "raw": message,
                "category": None,
                "archetype": "private_message",
                "created_at": datetime.datetime.now().isoformat()
            }
        )
