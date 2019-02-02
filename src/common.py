import network
import time

SSID = "ESP8266_CRICKET"
WIFI_PASS = "ESP8266_CRICKET_PASS"
GATEWAY_IP = "192.168.1.1"
SENDER_IP = "192.168.1.100"
RECEIVER_IP = "192.168.1.200"
RECEIVER_PORT = 2520
MESSAGE_LEN = 9 # Bytes

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

def shutdown_socket(s):
    if s is None:
        return
    s.close()
    time.sleep_ms(100)

def connect_to_network(station, ssid, password, timeout = 11):
    if station is not None:
        station.disconnect()
        station.active(False)
        time.sleep_ms(100)

    station.active(True)
    time.sleep_ms(100)

    print("Connecting to " + ssid + " " + password)
    station.connect(ssid, password)
    for _ in range(timeout):
        time.sleep(1)
        if station.isconnected():
            return
        print("Station status " + wlan_status_str(station))
    print("Failed to connect", timeout, "times")

def flash_n_times(pin, n, *, gap_ms = 480):
    # Assumes active low
    for _ in range(n):
        pin.value(False)
        time.sleep_ms(20)
        pin.value(True)
        time.sleep_ms(gap_ms)
    pin.value(True)

