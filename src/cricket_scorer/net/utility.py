#!/usr/bin/env python3

import random
import sys


def probability(prob, a, b):
    assert 0 <= prob <= 1
    # Not particularly precise but good enough
    if gen_random(2) < int(prob * 65536):
        return a
    else:
        return b


def gen_random(num_bytes, excluding=()):
    # TODO: this doesn't work nicely on micropython with large numbers
    # ie. num_bytes = 9
    if type(excluding) is int:
        excluding = (excluding, )
    assert type(excluding) in (tuple, list)
    assert num_bytes > 0

    def f():
        return random.randint(0, 2**(num_bytes * 8) - 1)

    val = f()
    while val in excluding:
        val = f()
    return val


def int_to_bytes(i, n):
    # i - integer to convert
    # n - number of bytes of output (will be zero padded)
    # Outputs bytes LE (x86 and esp8266 should be fine)

    # assert i >= 0 and n >= 0
    assert n >= 0
    b = bytearray()
    for _ in range(n):
        b.append(i & 0xff)
        i >>= 8
    return bytes(b)


def _test_probability(probs=[0, 0.01, 0.05, 0.1, 0.5, 0.9, 0.99, 1.0]):
    iters = 10000
    epsilon = 0.01
    for p in probs:
        average = sum(probability(p, True, False) for _ in range(iters)) / iters
        assert p - epsilon <= average <= p + epsilon


def main(argv):
    n = 0x0123456789ABCDEF
    n_bytes = b'\xef\xcd\xab\x89gE#\x01'
    print(int_to_bytes(n, 8))
    assert int.from_bytes(int_to_bytes(n, 8), sys.byteorder) == n
    print("Hello world!")

    _test_probability()

    print(int_to_bytes(-1, 0))
    print(int_to_bytes(-1, 1))
    print(int_to_bytes(-1, 2))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
