#!/usr/bin/env python3

import sys
import time
from smbus2 import SMBus

int_to_display = {
        0: 0x7e,
        1: 0x30,
        2: 0x6d,
        3: 0x79,
        4: 0x33,
        5: 0x5b,
        6: 0x1f,
        7: 0x70,
        8: 0x7f,
        9: 0x73,
        None: 0x00,
        }

#  def i2c_write(i2c, addr, sub_byte, val):
    #  i2c.write_byte(addr, sub_byte)
    #  i2c.write_byte(0x60, val)
    #  i2c.write_byte(addr, 0)

def i2c_write(bus, addr, mux_addr, val):
    # Address the multiplexer
    bus.write_byte_data(addr, 0, mux_addr)
    # Write the data
    bus.write_i2c_block_data(0x60, 0x44, [val])
    #  bus.write_byte_data(addr, 0x44, val)
    # Clear the bus, "deselect" the multiplexer
    bus.write_byte_data(addr, 0, 0)

# 75, 76, 77 - i2c addresses (in hex?)
# 117, 118, 119 addresses of the multiplexers in decimal
# 4, 5, 6

def main(argv):
    addrs = [0x75, 0x76, 0x77]
    muxes = [0x4, 0x5, 0x6]
    addrs_muxes = [(a, m) for a in addrs for m in muxes]

    bus = SMBus(1)
    #  i2c_write(bus, 0x75, 4, 0x7f)
    #  for a in addrs:
        #  for m in muxes:
            #  print(a, m)
    #  for i in range(0, 256):
        #  print(i)

    #  for k, v in int_to_display.items():
    for a, m in addrs_muxes:
        #  print(a, m, k, v)
        i2c_write(bus, a, m, int_to_display[None])
        time.sleep(0.1)
    time.sleep(1)

    #  i2c_write(bus, 0x75, 4, int_to_display[8])
    #
    #  input("1")
    #  print(bus.write_i2c_block_data(0x75, 0, [4]))
    #  time.sleep(0.5)
    #  input("2")
    #  print(bus.write_i2c_block_data(0x60, 0, [0x44, 0x7f]))
    #  time.sleep(0.5)
    #  input("3")
    #  print(bus.write_i2c_block_data(0x75, 0, [0]))

    #bus.write_byte(0x60, 0x7f)
    #bus.write_byte(0x60, 0x00)
    print("Hello world!")

if __name__ == "__main__":
    sys.exit(main(sys.argv))
