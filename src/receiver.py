import machine
import time
import socket
import sys

from machine import Pin, I2C

from common import *

def init_listen_socket(port):
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(0)
    return sock

def i2c_write(i2c, addr, sub_byte, val):
    i2c.writeto(addr, sub_byte)
    b = i2c.writeto(addr, val)
    i2c.writeto(addr, b"\x00")

pin = Pin(2, Pin.OUT)
pin.value(1) # Active low, turn off
station = station_init(RECEIVER_IP)

while not connect_to_network(station, SSID, WIFI_PASS, pin):
    time.sleep(5)
    flash_n_times(pin, 5)
print("Connected to network " + str(SSID) + ": " + str(station.ifconfig()))

i2c = I2C(scl = Pin(5), sda = Pin(4), freq = 100000)
# FIXME: what are the actual channels
mux_channels = [(m, c) for m in [116, 117, 118] for c in [b"4", b"5", b"6"]]

try:
    listen_sock = init_listen_socket(RECEIVER_PORT)
    listen_sock.settimeout(40)

    while True:
        print("Waiting for connections on " + str(listen_sock))
        sock, addr = listen_sock.accept()
        sock.settimeout(10)
        print("Received connection from " + str(addr))

        try:
            # msg of type bytes
            msg = sock.read(MESSAGE_LEN)
            print("Received " + str(msg))

            print("Setting digits")
            for (b, (mux, chan)) in zip(bytearray(msg), mux_channels):
                i2c_write(i2c, mux, chan, bytes([b]))

            time.sleep(1)
        except OSError as e:
            print("Socket read error: " + str(e))
        finally:
            if sock is not None:
                sock.close()
finally:
    if listen_sock is not None:
        listen_sock.close()
    print("Restarting")
    flash_n_times(pin, 15)
    machine.reset()

# Listen for connection from sender
# Receive data
