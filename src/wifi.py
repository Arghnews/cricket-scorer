import network

from common import *

def station_init(ip, gateway = GATEWAY_IP):
    print("Initialising station with ip", ip)
    station = network.WLAN(network.STA_IF)
    # Must be active for config on at least some esp8266 versions
    station.active(True)
    station.ifconfig((ip, "255.255.255.0", gateway, "8.8.8.8"))
    print("Initialised station:", station.ifconfig())
    return station

def wlan_status_str(station):
    if station is None:
        return "station is NULL - no status"

    WLAN_STATUS_TO_STR = {
            network.STAT_IDLE: "STAT_IDLE",
            network.STAT_CONNECTING: "STAT_CONNECTING",
            network.STAT_WRONG_PASSWORD: "STAT_WRONG_PASSWORD",
            network.STAT_NO_AP_FOUND: "STAT_NO_AP_FOUND",
            network.STAT_CONNECT_FAIL: "STAT_CONNECT_FAIL",
            network.STAT_GOT_IP: "STAT_GOT_IP",
            }

    return WLAN_STATUS_TO_STR.get(station.status(), "UNKNOWN STATUS")

def shutdown_station(station):
    if station is None:
        return
    # This disconnects an active network so is a catch all
    station.active(False)

def connect_to_network(station, ssid, password, timeout_seconds = 11):
    if station is not None:
        station.disconnect()
        station.active(False)
        time.sleep_ms(100)

    station.active(True)
    time.sleep_ms(100)

    print("Connecting to " + ssid + " " + password)
    station.connect(ssid, password)
    for _ in range(timeout_seconds):
        time.sleep(1)
        if station.isconnected():
            return True
        print("Station status " + wlan_status_str(station))
    print("Failed to connect", timeout_seconds, "times")
    return False

