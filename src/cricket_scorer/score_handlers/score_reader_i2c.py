from functools import partial

from . import utils

# This is what the control box should run.
# Won't have clean shutdown, but in practice the device will be switched off by
# removing the power anyway
class ScoreReaderI2c:
    def __init__(self, log):
        from smbus2 import SMBus
        self.log = log
        self.bus = SMBus(1)
        addrs = [113, 114, 115]
        chans = [4, 5, 6]
        self.mux_channels = [(m, c) for m in addrs for c in chans]

        self.write_byte = partial(utils.write_byte_safe, self.bus, self.log)
        self.read_byte = partial(utils.read_byte_else, self.bus, self.log)

    def _read(self, addr, sub_byte):
        # In all of testing this has never failed.

        # Set the address of the multiplexer and its device we're reading
        # from
        self.write_byte(addr, sub_byte)
        # Read the value
        b = self.read_byte(32)
        # Reset, deselect the multiplexer
        self.write_byte(addr, 0)
        return b

    # Returns an array of 9 bytes
    # 3 total, 1 wickets, 2 overs, 3 1st innings. Bytes breakdown.
    # Bytes are little endian integers, ie. 0x00 == 0, 0x01 == 1
    def __call__(self):
        results = []
        # Reading come out inverted (active low) so invert them back so we can
        # send a zero as 0, a one as 1, so on
        for mux, chan in self.mux_channels:
            results.append(255 - self._read(mux, chan))
        return bytes(results)

