def search(message_dict, message, tenant):
    search_input = message_dict["stream"]
    if not search_input:
        print("nope")
        return

    print(search_input)
