#!/usr/bin/env python3

import sys

from smbus2 import SMBus

# Copied from
# https://kernel.googlesource.com/pub/scm/utils/i2c-tools/i2c-tools/+/v3.1.2/tools/i2cdetect.c
def main(argv):
    print("Hello world!")

    bus = SMBus(1)

    for i in range(0, 128, 16):
        vals = []
        for j in range(0, 16):
            res = True
            try:
                k = i + j
                if (k >= 0x30 and k <= 0x37) or (k >= 0x50 and k <= 0x5f):
                    bus.read_byte(i + j)
                else:
                    bus.write_byte(i + j, 0)
            except Exception as e:
                res = False
            if res:
                vals.append("{}: {:3}".format(j, i + j))
            else:
                vals.append("{}: ---".format(j))
        print("{:3}".format(i), ", ".join(vals))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
