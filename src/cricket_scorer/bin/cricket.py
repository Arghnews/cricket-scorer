#!/usr/bin/env python3

import argparse
import sys

from cricket_scorer.misc import params
from cricket_scorer.net import connection

def main(argv):
    parser = argparse.ArgumentParser(allow_abbrev = False)
    #  parser.add_argument("mode", choices = ["sender", "receiver"])
    #  parser.add_argument("--profile", choices = params.profiles.keys(), required = True)

    subparsers = parser.add_subparsers(dest = "mode")
    subparsers.required = True

    get_keys = lambda profiles: [key for key in profiles.keys() if not key.startswith("_")]

    sender_parser = subparsers.add_parser("sender")
    sender_parser.add_argument("--profile", choices = get_keys(params.sender_profiles), required = True)

    receiver_parser = subparsers.add_parser("receiver")
    receiver_parser.add_argument("--profile", choices = get_keys(params.receiver_profiles), required = True)

    # I don't understand why argv doesn't go in here, but it doesn't
    parsed_args = parser.parse_args()

    mode, profile = parsed_args.mode, parsed_args.profile

    print("Running cricket program with mode:", mode, "profile:", profile, " args:", parsed_args)

    if mode == "sender":
        connection.sender_loop(params.sender_profiles[profile])
    elif parsed_args.mode == "receiver":
        connection.receiver_loop(params.receiver_profiles[profile])

if __name__ == "__main__":
    sys.exit(main(sys.argv))
