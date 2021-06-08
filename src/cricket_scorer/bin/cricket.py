#!/usr/bin/env python3

import argparse
import sys

from cricket_scorer.misc import profiles
from cricket_scorer.net import connection
from cricket_scorer.net import countdown_timer

def main():
    sender_profiles = profiles.sender_profiles
    receiver_profiles = profiles.receiver_profiles

    parser = argparse.ArgumentParser(allow_abbrev = False)
    #  parser.add_argument("mode", choices = ["sender", "receiver"])
    parser.add_argument("--logs-folder")

    subparsers = parser.add_subparsers(dest = "mode")
    subparsers.required = True

    sender_parser = subparsers.add_parser("sender")
    sender_parser.add_argument("--profile", choices =
            sender_profiles.get_buildable_profile_names(),
            required = True)

    receiver_parser = subparsers.add_parser("receiver")
    receiver_parser.add_argument("--profile", choices =
            receiver_profiles.get_buildable_profile_names(),
            required = True)

    # I don't understand why argv doesn't go in here, but it doesn't
    #  parsed_args = parser.parse_args()
    # args = "sender --profile sender_args_excel -s cricket.xlsx -w Sheet1"
    #  args = "sender --profile sender_args_excel -s cricket.xlsx -w Sheet1".split(" ")
    parsed_args, additional_args = parser.parse_known_args()

    print("parsed_args:", parsed_args)
    print("additional_args:", additional_args)

    mode, profile_name = parsed_args.mode, parsed_args.profile

    print("Running cricket program with mode:", mode, "profile:", profile_name,
            " args:", parsed_args)

    if mode == "sender":
        args = sender_profiles.build_profile(profile_name,
                logs_folder = parsed_args.logs_folder)

        print("Args:", args)

        score_reader = args.score_reader(args.logger)
        sender_connection = connection.Sender(args)

        timer = countdown_timer.make_countdown_timer(seconds=1, started=True)

        while True:
            timer.sleep_till_expired()
            if timer.just_expired():
                score = next(score_reader)
                args.logger.info("Score read is:", score)
                sender_connection.poll(score)
                timer.reset()

    elif mode == "receiver":
        args = receiver_profiles.build_profile(profile_name,
                logs_folder = parsed_args.logs_folder)
        print("Args:", args)
        connection.receiver_loop(args)

if __name__ == "__main__":
    sys.exit(main())
