import machine
import sys
import time

from machine import Pin

import connection
import simple_i2c
import udp_receive
import wifi

from common import *

pin = machine.Pin(2, machine.Pin.OUT)
pin.value(1) # Active low, turn off

# i = 0
# def test_f():
#     global i
#     i += 1
#     import utility
#     return utility.int_to_bytes(i, 9)

try:
    print("Initialising i2c")
    i2c = simple_i2c.SimpleI2C(
            multiplexers = SENDER_MULTIPLEXERS, channels = SENDER_CHANNELS,
            scl = machine.Pin(5), sda = machine.Pin(4), freq = 100000)

    print("Connecting to network", SSID)
    station = wifi.station_init(SENDER_IP)
    while not wifi.connect_to_network(station, SSID, WIFI_PASS):
        print("Attempting to connect to network", SSID)
        time.sleep(5)
        flash_n_times(pin, 5)

    print("Going into receive loop")
    with udp_receive.SimpleUDP(SENDER_PORT, RECEIVER_IP, RECEIVER_PORT) as sock:
        connection.sender_loop(sock, i2c.read)
        # connection.sender_loop(sock, test_f)

except Exception as e:
    sys.print_exception(e)
finally:
    print("Cleaning up")

    wifi.shutdown_station(station)
    gc.collect()

    print("Restarting")
    flash_n_times(pin, 8, gap_ms = 230)
    machine.reset()

