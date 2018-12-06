#!/usr/bin/env python3

import sys

# Cricket scoreboard looks like this (I'm told):
#
#  # # #
#      #
#    # #
#  # # #
#
# Where each # is a digit - want to replace leading zeroes with a null digit
# so they are not lit up as zero

def map_while(ba, i, j, zero = 0, replaced = 69):
    # Mutates bytearray ba in place transforming leading zeroes
    for i in range(i, j):
        if ba[i] != zero:
            return
        ba[i] = replaced

def f(vals, *number_lengths):
    n = 0
    for j in number_lengths:
        map_while(vals, n, n+j)
        n += j

def main(argv):
    ba = bytearray([1, 0, 3,  0,  0, 0,  2, 0, 0])
    f(ba, 3, 1, 2, 3)
    print(ba)
    print("Hello world!")

if __name__ == "__main__":
    sys.exit(main(sys.argv))
