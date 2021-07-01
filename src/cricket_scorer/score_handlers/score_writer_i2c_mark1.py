from smbus2 import SMBus

from . import utils


def i2c_write(bus, log, addr, mux_addr, val):
    # Address the multiplexer
    utils.write_byte_safe(bus, log, addr, mux_addr)
    # Write the data
    try:
        bus.write_i2c_block_data(0x60, 0x44, [val])
    except OSError as e:
        log.error("I2c bus write error. Bus:", bus, "addr:", hex(addr), "writing raw data:",
                  hex(val), ", error:", str(e))
    # Clear the bus, "deselect" the multiplexer
    utils.write_byte_safe(bus, log, addr, 0)


# Run on the mark 1 scoreboard
class ScoreWriterI2cMark1:
    def __init__(self, log):
        self._log = log
        self._bus = SMBus(1)
        addrs = [0x75, 0x76, 0x77]
        muxes = [0x4, 0x5, 0x6]
        self._addrs_muxes = [(a, m) for a in addrs for m in muxes]

    def __call__(self, score, blank_out_leading_zeroes=True):
        score = utils.sanitise_received_score(self._log, score, len(self._addrs_muxes),
                                              blank_out_leading_zeroes)

        if score is None:
            return

        for val, (addr, mux) in zip(score, self._addrs_muxes):
            self._log.debug("Writing to addr:", addr, "mux:", mux, "value:", val)
            i2c_write(self._bus, self._log, addr, mux, utils.INT_TO_DISPLAY[val])
