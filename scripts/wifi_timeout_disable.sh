#!/usr/bin/env bash

set -u -o pipefail

# The problem:
# On the scoreboard's remote control box we want to connect to the home wifi for
# debugging if it's in range. However we don't want the pi's internal radio to
# be constantly searching for the home wifi as this takes a lot of power, and
# this will be wasted if the control box is sitting in some field somewhere.
# The fix:
# Enable the wifi at bootup for a little while, if you can't find the network,
# then switch it off.

# Changed this into function as despite predictable network names, occasionally
# on startup the internal wifi appears as wlan1, not wlan0. Also duplicated the
# /etc/wpa_supplicant/wpa_supplicant-wlan0.conf to wlan1 too.

# Changed the return code of the run function to exit success unless there's
# actually something we don't expect like no SSID in the wpa_supplicant file.
# Now returns 0 if can't find the config file, or if can find it but can't or
# can connect as these are all expected outcomes and the script will
# enable/disable the wifi as appropriate.

function run() {
    iface="$1"
    echo "Interface is $iface"
    wpa_config_file="/etc/wpa_supplicant/wpa_supplicant-$iface.conf"
    # Ensure time_to_look_for_wifi_seconds > attempts
    time_to_look_for_wifi_seconds=180
    attempts=30

    if ((time_to_look_for_wifi_seconds < 5)); then
        time_to_look_for_wifi_seconds=5
    fi
    if ((attempts > time_to_look_for_wifi_seconds)); then
        attempts=3
    fi

    # If can't read the config file, then just disable the interface and exit
    if ! [ -f "$wpa_config_file" ]; then
        echo "Could not find config file $wpa_config_file, disabling wifi and exiting"
        sudo ip link set "$iface" down
        return 0
    fi

    # Pull out ssid line
    ssid="$(grep -m 1 -i -o "ssid=.*$" "$wpa_config_file")"
    # Remove ssid= prefix
    ssid="${ssid#*=}"
    # Strip quotes
    ssid="$(echo "$ssid" | sed "s/^\([\"']\)\(.*\)\1\$/\2/g")"
    echo "$ssid"

    if [ -z "$ssid" ]; then
        echo "Could not parse ssid, disabling wifi and exiting"
        sudo ip link set "$iface" down
        return 1
    fi

    timeout=$((time_to_look_for_wifi_seconds / $attempts))
    for ((i = 0; i < $attempts; i++)); do
        echo "Attempt $((i + 1)) of $attempts to find wifi ssid:$ssid"
        sudo ip link set "$iface" up
        sudo wpa_cli -i "$iface" scan
        echo "Sleeping for $timeout seconds while scanning for wifi"
        sleep "$timeout"
        results="$(sudo wpa_cli -i "$iface" scan_results)"

        # Do not quote this (you moron), the if statement depends on the exit code,
        # if you quote it it evaluates to "" which isn't what you want
        if $(echo "$results" | grep -q "$ssid")
        then
            echo "Found $ssid! Leaving wifi enabled and exiting"
            return 0
        else
            echo "Did not find wifi"
        fi
    done

    echo "Did not find wifi and timed out, disabling interface and exiting"
    sudo ip link set "$iface" down
    return 0
}

for iface in wlan0 wlan1
do
    run "$iface"
done

