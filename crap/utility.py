#!/usr/bin/env python3

import sys

if sys.platform == "esp8266":
    import uos
else:
    import random

def gen_random(num_bytes):
    assert num_bytes > 0
    if sys.platform == "esp8266":
        return int.from_bytes(uos.urandom(num_bytes), sys.byteorder)
    else:
        return random.randint(0, 2 ** (num_bytes * 8) - 1)

def int_to_bytes(n, bits):
    # For a positive integer n, outputs bits number of bits as bytes (LE)
    # n = (1 << 16) + (1 << 15) + 63
    # n = 0x0123456789ABCDEF
    # 0x0123456789ABCDEF -> 64 bit LE - EF CD AB 89 67 45 23 01
    # bits = 64
    assert n >= 0 and bits >= 0
    b = bytearray()
    while bits > 0:
        b.append(sum(n & 2 ** i for i in range(min(8, bits))))
        n >>= 8
        bits -= min(8, bits)
    return bytes(b)

def main(argv):
    print("Hello world!")

if __name__ == "__main__":
    sys.exit(main(sys.argv))
