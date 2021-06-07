#!/usr/bin/env python3

import argparse
import sys

from cricket_scorer.misc import params
from cricket_scorer.net import connection
from cricket_scorer.net import countdown_timer

def main():
    sender_profiles = params.sender_profiles
    receiver_profiles = params.receiver_profiles

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
        args = None
        if parsed_args.logs_folder is not None:
            args = sender_profiles.build_profile(profile_name,
                    logger_logs_folder = parsed_args.logs_folder)
        else:
            args = sender_profiles.build_profile(profile_name)

        print("Args:", args)

        log = None
        if args.logger.logs_folder is not None:
            log = args.logger.logger(args.logger.logs_folder)
        else:
            log = args.logger.logger()

        score_reader = args.score_reader(log)
        sender_connection = connection.Sender(log, args)

        timer = countdown_timer.make_countdown_timer(seconds=1, started=True)

        while True:
            timer.sleep_till_expired()
            if timer.just_expired():
                score = next(score_reader)
                log.info("Score read is:", score)
                sender_connection.poll(score)
                timer.reset()

    elif mode == "receiver":
        connection.receiver_loop(params.receiver_profiles[profile_name])

    #  if mode == "sender" and profile == "sender_args_excel":
        #  parser2 = argparse.ArgumentParser()
        #  parser2.add_argument("-s", "--spreadsheet", required = True)
        #  parser2.add_argument("-w", "--worksheet", required = True)
        #  res = parser2.parse_args(additional_args)

    #  if mode == "sender":
        #  #  connection.sender_loop(params.sender_profiles[profile])
        #  print("Would now run with SENDER:", params.sender_profiles[profile])
        #  args = params.sender_profiles[profile]

        #  #  reader_gen = reader.score_reader_i2c(args.logger())
        #  reader_gen = m.score_generator(additional_args)

        #  coro = connection.sender_loop(args.logger(), args)
        #  await coro.asend(None)

        #  while True:
            #  score = next(reader_gen)
            #  print("Score is:", score)
            #  await coro.asend(score)
            #  time.sleep(1)

        #  i = 0
        #  while True:
            #  i += 1
            #  print("Main sending", i)
            #  val = await coro.asend(i)
            #  print("Main received", val, "\n")
            #  time.sleep(1)

if __name__ == "__main__":
    sys.exit(main())
