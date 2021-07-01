from functools import partial

from smbus2 import SMBus

from cricket_scorer.score_handlers.scoredata import ScoreData
from . import utils


# This is what the remote control box should run.
# Won't have clean shutdown, but in practice the device will be switched off by
# removing the power anyway
class ScoreReaderI2c:
    """Run on the (remote) control box, reads score from I2C bus"""
    def __init__(self, log):
        self._log = log
        self._bus = SMBus(1)
        addrs = [113, 114, 115]
        chans = [4, 5, 6]
        self._mux_channels = [(m, c) for m in addrs for c in chans]

        self.write_byte = partial(utils.write_byte_safe, self._bus, self._log)
        self.read_byte = partial(utils.read_byte_else, self._bus, self._log)

    def read_score(self):
        results = []
        for mux, chan in self._mux_channels:
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

    def close(self):
        pass
