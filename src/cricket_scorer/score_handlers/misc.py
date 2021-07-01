import time

from cricket_scorer.net.packet import Packet
from cricket_scorer.net.utility import int_to_bytes
from cricket_scorer.score_handlers.scoredata import ScoreData


# Test score reader
class ScoreGenerator:
    def __init__(self, *args):
        if args:
            print("Additional args received:", *args)
        self.score = 0
        self._time = time.time()
        self.change_every_seconds = 4

    def refresh_excel(self, *args, **kwargs):
        pass

    def read_score(self):
        if time.time() - self._time > self.change_every_seconds:
            # if random.random() >= 0.8:
            self.score += 1
            self._time = time.time()
            print("Latest score increased to", self.score)
        return ScoreData(score=int_to_bytes(self.score, Packet.PAYLOAD_SIZE))

    def close(self):
        pass


# Test score writer
class ScorePrinter:
    def __init__(self, *args):
        pass

    def __call__(self, score):
        print("New score received:", score)
