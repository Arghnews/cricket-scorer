import machine
import time
import socket
import sys

from machine import Pin, I2C

from common import *

def i2c_read(i2c, addr, sub_byte):
    print("In i2c read")
    print(i2c, addr, sub_byte)
    i2c.writeto(addr, sub_byte)
    b = i2c.readfrom(32, 1)
    i2c.writeto(addr, b"\x00")
    print("Done i2c read")
    return b

# Raises OSError on timeout of connecting socket
# Connect to receiver and send data
def tcp_connect(ip, port, socket_timeout = 5):
    receiver_addr = socket.getaddrinfo(ip, port)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(socket_timeout)
    #sock.connect(receiver_addr)
    try:
        sock.connect(receiver_addr)
        return sock
    except OSError as e:
        print("Socket failed to connect to " + str(receiver_addr) + ": " +
                str(e))
        sock.close()
    return None


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

pin = Pin(2, Pin.OUT)
pin.value(1) # Active low, turn off

station = None
while True:
    station, connected = connect_to_network(SENDER_IP, GATEWAY_IP, station, SSID, WIFI_PASS)
    if connected:
        break
    time.sleep(5)
    flash_n_times(pin, 5)
print("Connected to network " + str(SSID) + ": " + str(station.ifconfig()))

sock = None
for _ in range(4):
    sock = tcp_connect(RECEIVER_IP, RECEIVER_PORT)
    if sock is not None:
        print("Socket connected")
        break
else:
    # Have tried 4 times - no luck - reboot?
    flash_n_times(pin, 9)
    print("Failed to connect socket - restarting")
    machine.reset()

try:
    i2c = I2C(scl = Pin(5), sda = Pin(4), freq = 100000)
    mux_channels = [(m, c) for m in [113, 114, 115] for c in [b"\x04", b"\x05", b"\x06"]]

    print("Init while true loop")
    while True:
        vals = bytearray()
        print("For mux chans")
        for mux, chan in mux_channels:
            print("mux chan: ", mux, chan)
            val = int.from_bytes(i2c_read(i2c, mux, chan), sys.byteorder)
            vals.append(code_to_digit[val])
        assert len(vals) == MESSAGE_LEN
        vals = bytes(suppress_leading_zeroes(vals, 3, 1, 2, 3))
        print("Sending " + str(len(vals)) + " bytes: " + str(vals))
        try:
            print("Writing data to socket:", vals)
            sock.write(vals)
            print("Written")
        except Exception as e:
            print("Socket write got error:" + str(e))
        time.sleep(1)
finally:
    print("Cleaning up")
    if sock is not None:
        sock.close()
    if station is not None and station.isconnected():
        station.disconnect()
    print("Restarting")
    flash_n_times(pin, 15)
    machine.reset()

