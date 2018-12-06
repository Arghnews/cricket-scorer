#!/bin/bash
set -e

# this.sh src/main.py [0]
# copies src/main.py to /main.py on the chip at /dev/ttyUSB0
# defaults to /dev/ttyUSB0

port="/dev/ttyUSB${2-0}"
ls "$port" 1>/dev/null
: ${1:?Supply filename to copy}

ampy="ampy -p $port -b 115200"

echo $ampy put src/common.py /common.py
echo $ampy put "$1" /main.py

read -p "Are you sure? " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]?$ ]]
then
    $ampy put src/common.py /common.py
    $ampy put "$1" /main.py
    $ampy reset
fi

