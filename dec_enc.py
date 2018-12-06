#!/usr/bin/env python3

import sys
import struct

# Packs a list of len 9 bools into a bytes object of len 2
def encode(vals):
    assert len(vals) == 9
    bytes_obj = sum(bool(v) * 2**i for i, v in enumerate(vals))
    return struct.pack("H", bytes_obj)

# Inverse of encode
def decode(bytes_obj):
    n = struct.unpack("H", bytes_obj)[0]
    print(n)
    nums = [n & 2**i for i in range(9)]
    return [bool(b) for b in nums]

table = {
        0xff: 0x7e,
        0xfe: 0x30,
        0xfd: 0x6d,
        0xfc: 0x79,
        0xfb: 0x33,

        0xfa: 0x5b,
        0xf9: 0x5f,
        0xf8: 0x70,
        0xf7: 0x7f,
        0xf6: 0x7b,

        0xf5: 0x00,
        }

def main(argv):
    # sock.read() -> len(9) bytes obj
    data = bytes([0xff, 0xfe,
        0xfe, 0xfd, 0xfc, 0xfb, 0xfa, 0xf9, 0xf8, 0xf7, 0xf6, 0xf5])
    data = bytearray(data)
    print(data)
    for d in data:
        print(d, table[d])

    # bytes object with the data read
    #vals = [True, True, False, False, False, False, False, False, True]
    #assert vals == decode(encode(vals))
    #v = encode(vals)
    #print(decode(v))
    #print(struct.pack("H", encode(vals)))

if __name__ == "__main__":
    sys.exit(main(sys.argv))
