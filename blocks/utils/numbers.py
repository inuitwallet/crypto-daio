import codecs


def get_var_int(raw_bytes):
    """
    given a sequence of 9 bytes, calculate the integer to return
    https://en.bitcoin.it/wiki/Protocol_documentation#Variable_length_integer
    :param raw_bytes:
    :return:
    """
    check_var_int = codecs.encode(raw_bytes[:1], 'hex')
    if check_var_int == b'fd':
        return int.from_bytes(raw_bytes[1:3], 'little'), 3
    elif check_var_int == b'fe':
        return int.from_bytes(raw_bytes[1:5], 'little'), 5
    elif check_var_int == b'ff':
        return int.from_bytes(raw_bytes[1:9], 'little'), 9
    else:
        return int.from_bytes(raw_bytes[:1], 'little'), 1
