#!/usr/bin/env bash

set -eu -o pipefail

# Should've done this in Python too

function main()
{
    # for arg in "$@"
    # do
    #     echo "1: $arg"
    # done
    port="/dev/ttyUSB0"
    ampy="ampy --port $port --baud 115200"
    role=sender
    # role=receiver
    # role=access_point
    copy_all
}

function echo_then_do()
{
    echo "$@"
    "$@"
}

function rm_all()
{
    for f in $($ampy ls)
    do
        # Assume files end in .py, else directory
        rm_command="rm"
        if ! [ "${f##*.}" = "py" ]; then rm_command="rmdir"; fi
        echo_then_do $ampy "$rm_command" "${f#/}"
    done

    echo "Now on board:"
    echo_then_do $ampy ls
}

function copy_all()
{
    declare -a arr

    for py in *.py udp_protocol/*.py
    do
        if [ "$role" = "sender" ] && [ "$py" = "sender.py" ]; then
            arr+=("$py")
        elif [ "$role" = "receiver" ] && [ "$py" = "receiver.py" ]; then
            arr+=("$py")
        elif [ "$role" = "access_point" ] && [ "$py" = "access_point.py" ]; then
            arr+=("$py")
        else
            if [ "$py" != "sender.py" ] && [ "$py" != "receiver.py" ] \
                && [ "$py" != "access_point.py" ]; then
                arr+=("$py")
            fi
        fi
    done

    rm -rf outgoing
    mkdir outgoing

    for py in "${arr[@]}"
    do
        cp "$py" outgoing/"${py##*/}"
    done

    cd outgoing

    for py in *
    do
        # Remove everything from the line with "def main" onward
        sed -i '/^def main(.*$/,$d' "$py"
        # Remove comment lines
        sed -i "/^[ ]*#/d" "$py"
        # Remove blank lines
        sed -i "/^$/d" "$py"

        # This to make copying files faster/use less mem on esp8266.
        # ~1500 lines to ~600
    done

    mv -v "${role}.py" main.py

    echo "About to rm all files on esp, then copy all these over"
    for py in *
    do
        echo $ampy put "$py"
    done

    read -p "Are you sure? " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]?$ ]]
    then
        rm_all
        echo_then_do $ampy mkdir udp_protocol
        for py in *
        do
            echo_then_do $ampy put "$py"
        done
    fi
}

main "$@"
