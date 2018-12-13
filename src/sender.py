import array
import machine
import socket
import sys
import time

from machine import Pin, I2C

from common import *

def i2c_read(i2c, addr, sub_byte):
    try:
        i2c.writeto(addr, sub_byte)
        b = i2c.readfrom(32, 1)
        i2c.writeto(addr, b"\x00")
        return b
    except Exception as e:
        print("Exception during i2c_read with addr", addr, ", sub_byte", sub_byte)
        raise

# Setup tcp connection. Returns None if failed else returns socket
def tcp_connect(ip, port, socket_timeout):
    receiver_addr = socket.getaddrinfo(ip, port)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(socket_timeout)
    t1 = time.ticks_ms()
    try:
        sock.connect(receiver_addr)
        return sock, None
    except OSError as e:
        print("Socket failed to connect to", receiver_addr, "-", e)
        sock.close()
        while time.ticks_diff(time.ticks_ms(), t1) < 5000:
            time.sleep(1)
        return None, e

# Tries to setup tcp connection, throws if fails over tries times
def try_tcp_connect(ip, port, *, retries = 4, socket_timeout = 5):
    print("Making tcp socket connection to", ip, "-", port)
    for _ in range(retries + 1):
        sock, e = tcp_connect(RECEIVER_IP, RECEIVER_PORT, socket_timeout)
        if sock is not None:
            return sock
    raise e

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

try:

    # Necessary for cleanup
    station = None
    sock = None

    print("Initialising i2c")
    i2c = I2C(scl = Pin(5), sda = Pin(4), freq = 100000)
    mux_channels = [(m, c)
            for m in array.array("B", [113, 114, 115])
            for c in [b"\x04", b"\x05", b"\x06"]]

    print("Connecting to network", SSID)
    station = station_init(SENDER_IP)
    while not station.isconnected():
        connect_to_network(station, SSID, WIFI_PASS)
        if not station.isconnected():
            time.sleep(5)
            flash_n_times(pin, 5)

    # This will throw if it fails, must cleanup socket object
    sock = try_tcp_connect(RECEIVER_IP, RECEIVER_PORT)

    print("Moving into sending loop")
    while True:
        vals = bytearray()
        print("Reading status over i2c")
        for mux, chan in mux_channels:
            val = int.from_bytes(i2c_read(i2c, mux, chan), sys.byteorder)
            vals.append(code_to_digit[val])
        assert len(vals) == MESSAGE_LEN
        vals = bytes(suppress_leading_zeroes(vals, 3, 1, 2, 3))
        print("Sending", len(vals), "bytes:", list(vals))
        sock.write(vals)
        time.sleep(1)

except Exception as e:
    sys.print_exception(e)
finally:
    print("Cleaning up")

    shutdown_socket(sock)
    del sock
    shutdown_station(station)
    del station
    gc.collect()

    print("Restarting")
    flash_n_times(pin, 15)
    machine.reset()

