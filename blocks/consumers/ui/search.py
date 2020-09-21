import json

from django.template.loader import render_to_string

from blocks.models import Address, Block, Transaction


def search(message_dict, message, tenant):
    search_input = message_dict["stream"]
    if not search_input:
        print("nope")
        return

    print(search_input)
