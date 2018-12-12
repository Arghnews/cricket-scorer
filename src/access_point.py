import machine
import network
import time

from common import *

def access_point_init():
    # Make access point (ie. router)
    nic = network.WLAN(network.AP_IF)
    # Must be active while configuring
    # tuple IP address, subnet mask, gateway and DNS server
    # DNS doesn't matter as no net but cannot set as 0.0.0.0
    nic.active(True)
    nic.ifconfig((GATEWAY_IP, "255.255.255.0", GATEWAY_IP, "8.8.8.8"))
    nic.config(essid = SSID, channel = 1, authmode = 4,
            password = WIFI_PASS)

    # [(MAC, RSSI)] of all connected
    #print(nic.status("stations"))
    # Not implemented for esp sadly
    return nic

pin = machine.Pin(2, machine.Pin.OUT)
flash_n_times(pin, 2)
access_point = access_point_init()
