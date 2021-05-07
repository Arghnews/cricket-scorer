from functools import partial

from smbus2 import SMBus

from . import utils

# This is what the remote control box should run.
# Won't have clean shutdown, but in practice the device will be switched off by
# removing the power anyway
def score_reader_i2c(log):
    bus = SMBus(1)
    addrs = [113, 114, 115]
    chans = [4, 5, 6]
    mux_channels = [(m, c) for m in addrs for c in chans]

    write_byte = partial(utils.write_byte_safe, bus, log)
    read_byte = partial(utils.read_byte_else, bus, log)

    while True:
        results = []
        for mux, chan in mux_channels:
            # In all of testing this sequence has never failed.

            # Set the address of the multiplexer and its device we're reading
            # from
            write_byte(mux, chan)
            # Read the value
            b = read_byte(32)
            # Reset, deselect the multiplexer
            write_byte(mux, 0)

            # Reading come out inverted (active low) so invert them back so we
            # can send a zero as 0, a one as 1, so on
            results.append(255 - b)
        yield bytes(results)

