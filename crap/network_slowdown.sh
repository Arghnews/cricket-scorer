#!/usr/bin/env bash

set -u -o pipefail

# https://wiki.linuxfoundation.org/networking/netem
# https://lartc.org/howto/lartc.qdisc.html + 6~ pages (not fully read)
# https://lartc.org/howto/lartc.qdisc.filters.html
# https://www.linuxquestions.org/questions/linux-networking-3/limiting-upload-with-tc-4175470860/
# https://www.cs.unm.edu/~crandall/netsfall13/TCtutorial.pdf
# And what feels like a shed load of linux man pages...

# sudo tc qdisc add dev $interface root
# fixed_delay=500ms
# plus_minus=500ms
# sudo tc qdisc add dev $interface root netem delay $fixed_delay $plus_minus distribution normal

# Restore to normal
# sudo tc qdisc delete dev $interface root

# interface=lo:0
# sudo ifconfig $interface 123.123.123.123
# sudo tc qdisc add dev $interface handle ffff: ingress
# sudo tc filter add dev lo parent ffff: protocol 17 u32 match udp dport 2520 action mirred egress redirect dev $interface
# sudo tc qdisc add dev ifb0 root netem delay 100ms

IF_INET=lo

# upload bandwidth limit for interface
BW_MAX=2000

# upload bandwidth limit for 172.16.16.11
BW_CLIENT=900

tc="sudo tc"

set -e

# first, clear previous settings

function echo_then_do()
{
    echo "$@"
    $@
}

echo_then_do $tc qdisc del dev ${IF_INET} root || :

# exit 0

# sudo tc qdisc add dev lo root handle 1: tbf rate 256kbit buffer 1600 limit 3000
# sudo tc qdisc add dev lo parent 1:1 handle 10: netem delay 100ms

# top-level htb queue discipline; send unclassified data into class 1:10
echo_then_do $tc qdisc add dev ${IF_INET} root handle 1: htb default 10
# echo_then_do $tc qdisc add dev ${IF_INET} root handle 1: prio

# parent class (wrap everything in this class to allow bandwidth borrowing)
# The prio qdisc creates 3 classes in it by default, 1:1, 1:2, 1:3 so we replace
# rather than add
# echo_then_do $tc class add dev ${IF_INET} parent 1: classid 1:1 htb \
#   rate ${BW_MAX}kbit ceil ${BW_MAX}kbit
# echo_then_do $tc class add dev ${IF_INET} parent 1: classid 1:1 htb \
#   rate ${BW_MAX}kbit ceil ${BW_MAX}kbit
echo_then_do $tc class add dev ${IF_INET} parent 1: classid 1:10 htb \
  rate ${BW_MAX}kbit ceil ${BW_MAX}kbit
echo_then_do $tc class add dev ${IF_INET} parent 1: classid 1:20 htb \
  rate ${BW_MAX}kbit ceil ${BW_MAX}kbit

# two child classes
#

# the default child class
# echo_then_do $tc class change dev ${IF_INET} parent 1:1 \
#   classid 1:2 htb rate $((${BW_MAX} - ${BW_CLIENT}))kbit ceil ${BW_MAX}kbit

# the child class for traffic from 172.16.16.11
# echo_then_do $tc class add dev ${IF_INET} parent 1:1 \
#   classid 1:20 htb rate ${BW_CLIENT}kbit ceil ${BW_MAX}kbit
# echo_then_do $tc qdisc add dev ${IF_INET} parent 1:1 handle 10: \
#   netem delay 100ms
# echo_then_do $tc qdisc add dev ${IF_INET} parent 1:20 netem delay 1000ms
# echo_then_do $tc qdisc add dev ${IF_INET} parent 1:20 netem delay 750ms

# Usage: ... netem [ limit PACKETS ]
#                  [ delay TIME [ JITTER [CORRELATION]]]
#                  [ distribution {uniform|normal|pareto|paretonormal} ]
#                  [ corrupt PERCENT [CORRELATION]]
#                  [ duplicate PERCENT [CORRELATION]]
#                  [ loss random PERCENT [CORRELATION]]
#                  [ loss state P13 [P31 [P32 [P23 P14]]]
#                  [ loss gemodel PERCENT [R [1-H [1-K]]]
#                  [ ecn ]
#                  [ reorder PRECENT [CORRELATION] [ gap DISTANCE ]]
#                  [ rate RATE [PACKETOVERHEAD] [CELLSIZE] [CELLOVERHEAD]]


echo_then_do $tc qdisc add dev ${IF_INET} parent 1:20 \
    netem \
    delay 200ms 400ms distribution normal \
    corrupt 0.5% \
    duplicate 15% 40% \
    loss 10% 40% \
    reorder 25% 50%

# classify traffic
# echo_then_do $tc filter add dev ${IF_INET} parent 1:0 protocol ip prio 1 u32 \
#   match ip src 127.0.0.1/32 flowid 1:20
ip_proto=ip
icmp_proto=1
tcp_proto=6
udp_proto=17

# echo_then_do $tc filter add dev ${IF_INET} protocol ip parent 1: matchall classid 1:10
# I don't understand - only ip seems to work as protocol
echo_then_do $tc filter add dev ${IF_INET} protocol ip parent 1: u32 \
  match ip dport 2520 0xffff flowid 1:20
echo_then_do $tc filter add dev ${IF_INET} protocol ip parent 1: u32 \
  match ip dport 2521 0xffff flowid 1:20

# Sample output:
# JustinPC(debug)crap$ ./network_slowdown.sh && ./reply_time.py
# sudo tc qdisc del dev lo root
# sudo tc qdisc add dev lo root handle 1: htb default 10
# sudo tc class add dev lo parent 1: classid 1:10 htb rate 2000kbit ceil 2000kbit
# sudo tc class add dev lo parent 1: classid 1:20 htb rate 2000kbit ceil 2000kbit
# sudo tc qdisc add dev lo parent 1:20 netem delay 750ms
# sudo tc filter add dev lo protocol ip parent 1: u32 match ip dport 2520 0xffff flowid 1:20
# sudo tc filter add dev lo protocol ip parent 1: u32 match ip dport 2521 0xffff flowid 1:20
# Port: 2519, 0.0002s 0.2397ms
# Port: 2520, 0.7503s 750.3270ms
# Port: 2521, 0.7506s 750.6324ms
# Port: 2522, 0.0001s 0.0975ms

# Notice latency on ports 2520 and 2521, showing rules have worked
