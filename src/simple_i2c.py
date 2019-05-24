import machine
import sys

class SimpleI2C:

    def __init__(self, *, multiplexers, channels, **kwargs):
        self.i2c = machine.I2C(**kwargs)
        self.mux_channels = [(m, bytes([c]))
                for m in multiplexers for c in channels]
        for m, c in self.mux_channels:
            assert type(m) is int and type(c) is bytes

    def read(self):
        vals = []
        for mux, chan in self.mux_channels:
            val = int.from_bytes(self._i2c_read(mux, chan), sys.byteorder)
            vals.append(code_to_digit[val])
        # assert len(vals) == MESSAGE_LEN
        return bytes(suppress_leading_zeroes(vals, 3, 1, 2, 3))

    def write(self, msg):
        assert type(msg) is bytes
        for (b, (mux, chan)) in zip(msg, self.mux_channels):
            self._i2c_write(mux, chan, bytes([0x44, b]))

    # mux, chan
    def _i2c_read(self, addr, sub_byte):
        return bytes([0xff])
        try:
            self.i2c.writeto(addr, sub_byte)
            b = self.i2c.readfrom(32, 1)
            self.i2c.writeto(addr, b"\x00")
            return b
        except Exception as e:
            print("Exception during i2c_read with addr", addr,
                    ", sub_byte", sub_byte)
            raise

    # mux, chan, val
    def _i2c_write(self, addr, sub_byte, val):
        return
        try:
            self.i2c.writeto(addr, sub_byte)
            self.i2c.writeto(96, val)
            self.i2c.writeto(addr, b"\x00")
        except Exception as e:
            print("Exception during i2c_write with addr", addr, ", sub_byte",
                    sub_byte, "val", val)
            raise

# Cricket scoreboard looks like this (I'm told):
#
#  # # #
#      #
#    # #
#  # # #
#
# Where each # is a digit - want to replace leading zeroes with a null digit
# so they are not lit up as zero

# Helper function - mutates in place slice of list ba in place transforming
# leading zeroes
def map_while(ba, i, j, zero, replaced_with):
    for i in range(i, j):
        if ba[i] != zero:
            return
        ba[i] = replaced_with

# Should be called AFTER mapping through code_to_digit
def suppress_leading_zeroes(vals, *number_lengths):
    leading_zero = 0x7e
    replaced_with = 0x00

    n = 0
    for j in number_lengths:
        map_while(vals, n, n+j, leading_zero, replaced_with)
        n += j
    # Possibly contentious - I prefer returning by value and this I believe
    # is tiny overhead
    return vals

code_to_digit = {
        0xff: 0x7e,
        0xfe: 0x30,
        0xfd: 0x6d,
        0xfc: 0x79,
        0xfb: 0x33,

        0xfa: 0x5b,
        0xf9: 0x5f,
        0xf8: 0x70,
        0xf7: 0x7f,
        0xf6: 0x7b,
        }

