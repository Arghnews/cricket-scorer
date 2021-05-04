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
class ScoreGenerator:
    def __init__(self, *args):
        self.score = 0
    def __call__(self):
        if random.random() >= 0.2:
            self.score += 1
            print("Latest score increased to", self.score)
        #  return int_to_bytes(latest_score_score, Packet.PAYLOAD_SIZE)
        return int_to_bytes(self.score, Packet.PAYLOAD_SIZE)

# Test score writer
class ScorePrinter:
    def __init__(self, *args):
        pass
    def __call__(self, score):
        print("New score received:", score)


