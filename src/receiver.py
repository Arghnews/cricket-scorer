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
    print("  i2c.writeto(addr = " + str(addr) + ", sub_byte = " + str(sub_byte) + ")")
    i2c.writeto(addr, sub_byte)
    print("  i2c.writeto(96, val = " + str(val) +  ")")
    i2c.writeto(96, val)
    print("  i2c.writeto(addr = " + str(addr) + ", b\"\x00\")")
    i2c.writeto(addr, b"\x00")

pin = Pin(2, Pin.OUT)
pin.value(1) # Active low, turn off
#station = station_init(RECEIVER_IP)

station = None
while True:
    station, connected = connect_to_network(RECEIVER_IP, GATEWAY_IP, station, SSID, WIFI_PASS)
    if connected:
        break
    time.sleep(5)
    flash_n_times(pin, 5)
print("Connected to network " + str(SSID) + ": " + str(station.ifconfig()))

i2c = I2C(scl = Pin(5), sda = Pin(4), freq = 100000)
# FIXME: what are the actual channels
mux_channels = [(m, c) for m in [117, 118, 119] for c in [b"\x04", b"\x05", b"\x06"]]

listen_sock = init_listen_socket(RECEIVER_PORT)
listen_sock.settimeout(40)
try:

    while True:
        print("Waiting for connections on " + str(listen_sock))
        sock, addr = listen_sock.accept()
        sock.settimeout(10)
        print("Received connection from " + str(addr))

        try:
            # msg of type bytes
            print("Reading in data from socket...")
            msg = sock.read(MESSAGE_LEN)
            print("Received " + str(msg))

            print("Setting digits")
            for (b, (mux, chan)) in zip(bytearray(msg), mux_channels):
                print("In iter: ", b, mux, chan)
                i2c_write(i2c, mux, chan, bytes([0x44, b]))
                print("done i2c_write")
            print("Digits setting done")

            #time.sleep(1)
        except Exception as e:
            raise
        finally:
            if sock is not None:
                sock.close()
except Exception as e:
    raise
finally:
    if listen_sock is not None:
        listen_sock.close()
    print("Restarting")
    flash_n_times(pin, 15)
    machine.reset()

# Listen for connection from sender
# Receive data
