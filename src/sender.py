import machine
import time
import socket
import sys

from machine import Pin, I2C

from common import *

def i2c_read(i2c, addr, sub_byte):
    i2c.writeto(addr, sub_byte)
    b = i2c.readfrom(addr, 1)
    i2c.writeto(addr, b"\x00")
    return b

# Raises OSError on timeout of connecting socket
# Connect to receiver and send data
def tcp_connect(ip, port, socket_timeout = 5):
    receiver_addr = socket.getaddrinfo(ip, port)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(socket_timeout)
    try:
        sock.connect(receiver_addr)
        return sock
    except OSError as e:
        print("Socket failed to connect to " + str(receiver_addr) + ": " +
                str(e))
        sock.close()
    return None

pin = Pin(2, Pin.OUT)
pin.value(1) # Active low, turn off
station = station_init(SENDER_IP)

while not connect_to_network(station, SSID, WIFI_PASS, pin):
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
    mux_channels = [(m, c) for m in [113, 114, 115] for c in [b"4", b"5", b"6"]]

    while True:
        vals = bytearray()
        for mux, chan in mux_channels:
            vals.append(int.from_bytes(i2c_read(i2c, mux, chan), sys.byteorder))
        assert len(vals) == MESSAGE_LEN
        print("Sending " + str(len(vals)) + " bytes: " + str(vals))
        sock.write(bytes(vals))
finally:
    print("Cleaning up")
    if sock is not None:
        sock.close()
    if station is not None and station.isconnected():
        station.disconnect()
    print("Restarting")
    flash_n_times(pin, 15)
    machine.reset()

