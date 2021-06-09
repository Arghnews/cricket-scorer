from functools import partial

from smbus2 import SMBus

from cricket_scorer.score_handlers.scoredata import ScoreData
from . import utils

# This is what the remote control box should run.
# Won't have clean shutdown, but in practice the device will be switched off by
# removing the power anyway
class ScoreReaderI2c:
    def __init__(self, log):
        self.log = log
        self.bus = SMBus(1)
        self.addrs = [113, 114, 115]
        self.chans = [4, 5, 6]
        self.mux_channels = [(m, c) for m in self.addrs for c in self.chans]

        self.write_byte = partial(utils.write_byte_safe, self.bus, self.log)
        self.read_byte = partial(utils.read_byte_else, self.bus, self.log)

    def read_score(self):
        results = []
        for mux, chan in self.mux_channels:
            # In all of testing this sequence has never failed.

            # Set the address of the multiplexer and its device we're reading
            # from
            self.write_byte(mux, chan)
            # Read the value
            b = self.read_byte(32)
            # Reset, deselect the multiplexer
            self.write_byte(mux, 0)

            # Reading come out inverted (active low) so invert them back so we
            # can send a zero as 0, a one as 1, so on
            results.append(255 - b)
        return ScoreData(score=bytes(results))

