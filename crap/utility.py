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

def int_to_bytes(i, n):
    # i - integer to convert
    # n - number of bytes of output (will be zero padded)
    # Outputs bytes LE (tested on x86 and esp8266 and no issues)

    assert i >= 0 and n >= 0
    b = bytearray()
    for _ in range(n):
        b.append(i & 0xff)
        i >>= 8
    return bytes(b)

def main(argv):
    n = 0x0123456789ABCDEF
    n_bytes = b'\xef\xcd\xab\x89gE#\x01'
    print(int_to_bytes(n, 8))
    assert int.from_bytes(int_to_bytes(n, 8), sys.byteorder) == n
    print("Hello world!")

if __name__ == "__main__":
    sys.exit(main(sys.argv))
