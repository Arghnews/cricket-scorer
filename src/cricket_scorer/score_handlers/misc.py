import random

from cricket_scorer.net.packet import Packet

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

# Test score reader
def score_generator(*args):
    if args:
        print("Additional args received:", *args)
    score = 0
    while True:
        if random.random() >= 0.2:
            score += 1
            print("Latest score increased to", score)
            yield int_to_bytes(score, Packet.PAYLOAD_SIZE)

# Test score writer
class ScorePrinter:
    def __init__(self, *args):
        pass
    def __call__(self, score):
        print("New score received:", score)


