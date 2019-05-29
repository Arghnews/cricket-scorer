#!/usr/bin/env bash

set -e -o pipefail

# Sometimes we catch the esp while it seems blocked/stuck etc.
# Really we'd like some way to send a soft reset and then spam it with Control-C
# Also, this script is pretty rough around the edges/messy, not proud of it.

# Should've done this in Python too

# port - /dev/ttyUSB[0-9]
# role - {send, sender, recv, receiver, access_point, ap}
# job - copy_all, rm_all
# verbose
# [nothing] or --help, -h
#
# Remember when flashing the actual esp units you may need to add
# https://github.com/espressif/esptool#flash-modes
# https://github.com/espressif/esptool/wiki/SPI-Flash-Modes
# esptool.py write_flash --help
# In short, if in doubt add after write_flash "--flash_mode dout" or "dio"
# esptool.py -p /dev/ttyUSB0 --baud 115200 \
    # write_flash --flash_size=detect 0 esp8266-20190125-v1.10.bin

# Single file commands
# ampy --port /dev/ttyUSB0 --baud 115200 put wifi.py
# ampy --port /dev/ttyUSB0 --baud 115200 ls wifi.py

function echo_err()
{
    echo "$@" >&2
}

function main()
{

    port="/dev/ttyUSB0"
    role=""
    job=""

    # Heredoc MUST be indented by actual tabs
    read -r -d '' help_string <<- EOF || :
	-p, --port              Port, default to $port
	-r, --role              send, recv, ap
	-j, --job               cp, rm, rm_cp
	-h, --help              Print this help
	EOF

    [ "$#" -eq 0 ] && echo "$help_string" && return 1

    for arg in "$@"
    do
        case "$arg" in
            -h|--h|-help|--help)
                echo "$help_string"
                return 1
                shift
                ;;
            -p|--port)
                port="$2"
                # Enforce that port is non-null
                : "${port:?Must set port - see --help}"
                echo "Port set to $port"
                shift 2
                ;;
            -r|--role)
                role="$2"
                case "$role" in
                    # Map role to filename version
                    send)
                        role="sender"
                        ;;
                    recv)
                        role="receiver"
                        ;;
                    ap)
                        role="access_point"
                        ;;
                    *)
                        echo_err "Role not recognised, see help"
                        # Does this leave exit status as 1?
                        return 1
                        ;;
                esac
                echo "Role set to $role"
                shift 2
                ;;
            -j|--job)
                job="$2"
                case "$job" in
                    cp|rm|rm_cp)
                        ;;
                    *)
                        echo_err "Job not recognised, see help"
                        # Does this leave exit status as 1?
                        return 1
                        ;;
                esac
                echo "Job set to $job"
                shift 2
                ;;
        esac
    done

    : "${port:?Must set port - see --help}"
    : "${role:?Must set role - see --help}"
    : "${job:?Must set job - see --help}"

    echo "Port set to $port"

    ampy="ampy --port $port --baud 115200"
    if [[ "$job" =~ "rm" ]]; then
        rm_all
    fi
    if [[ "$job" =~ "cp" ]]; then
        if [ "$role" = "access_point" ]; then
            echo_then_do $ampy put common.py
            echo_then_do $ampy put boot.py
            rm -rf outgoing
            mkdir outgoing
            cp access_point.py outgoing/main.py
            cd outgoing
            echo_then_do $ampy put main.py
        else
            copy_all
        fi
    fi

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

    echo_then_do $ampy ls
    echo ""
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

    # echo "About to rm all files on esp, then copy all these over"
    # for py in *
    # do
    #     echo $ampy put "$py"
    # done

    # read -p "Are you sure? " -n 1 -r
    # echo ""
    # if [[ $REPLY =~ ^[Yy]?$ ]]
    # then
    # echo_then_do $ampy mkdir udp_protocol
    for py in *
    do
        echo_then_do $ampy put "$py"
    done
    # fi
}

main "$@"
