
def to_hex(data):
    out_str = ""
    for each_byte in data:
        out_str += "{:02x}".format(each_byte)
    return out_str

