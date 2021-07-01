#!/usr/bin/env python3

import argparse
import sys

from cricket_scorer.misc import my_logger, profiles
from cricket_scorer.net import connection, countdown_timer


def main():
    sender_profiles = profiles.SENDER_PROFILES
    receiver_profiles = profiles.RECEIVER_PROFILES
    parser = argparse.ArgumentParser(allow_abbrev=False)
    #  parser.add_argument("mode", choices = ["sender", "receiver"])
    parser.add_argument("--logs-folder")

    subparsers = parser.add_subparsers(dest="mode")
    subparsers.required = True

    sender_parser = subparsers.add_parser("sender")
    sender_parser.add_argument("--profile",
                               choices=sender_profiles.get_buildable_profile_names(),
                               required=True)

    receiver_parser = subparsers.add_parser("receiver")
    receiver_parser.add_argument("--profile",
                                 choices=receiver_profiles.get_buildable_profile_names(),
                                 required=True)

    log = my_logger.get_logger()

    # I don't understand why argv doesn't go in here, but it doesn't
    #  parsed_args = parser.parse_args()
    # args = "sender --profile sender_args_excel -s cricket.xlsx -w Sheet1"
    #  args = "sender --profile sender_args_excel -s cricket.xlsx -w Sheet1".split(" ")
    parsed_args, additional_args = parser.parse_known_args()

    log.debug("parsed_args:", parsed_args)
    log.debug("additional_args:", additional_args)

    mode, profile_name = parsed_args.mode, parsed_args.profile

    log.info("Running cricket program with mode:", mode, "profile:", profile_name, " args:",
             parsed_args)

    if mode == "sender":
        with sender_profiles.build_profile(profile_name,
                                           logs_folder=parsed_args.logs_folder) as args:

            log.info("Args:", args)
            log.info("Initialising args")
            args.init_all()

            sender_connection = connection.Sender(args)
            timer = countdown_timer.make_countdown_timer(
                started=True, millis=args.receive_loop_timeout_milliseconds)

            old_scoredata = None
            while True:
                timer.sleep_till_expired()
                if timer.just_expired():
                    scoredata = args.score_reader.read_score()
                    if scoredata != old_scoredata:
                        args.logger.info("Latest scoredata:", scoredata)
                        old_scoredata = scoredata
                    sender_connection.poll(scoredata.score)
                    timer.reset()

    elif mode == "receiver":
        with receiver_profiles.build_profile(profile_name,
                                             logs_folder=parsed_args.logs_folder) as args:
            log.info("Args:", args)
            args.init_all()
            connection.receiver_loop(args)


if __name__ == "__main__":
    sys.exit(main())
