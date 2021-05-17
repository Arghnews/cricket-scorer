#!/usr/bin/env python3

import argparse
import asyncio
import sys

from cricket_scorer.misc import params
from cricket_scorer.net import connection

async def main():
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
    #  parsed_args = parser.parse_args()
    # args = "sender --profile sender_args_excel -s cricket.xlsx -w Sheet1"
    args = "sender --profile sender_args_excel -s cricket.xlsx -w Sheet1".split(" ")
    parsed_args, additional_args = parser.parse_known_args(args)

    print("parsed_args:", parsed_args)
    print("additional_args:", additional_args)

    mode, profile = parsed_args.mode, parsed_args.profile

    print("Running cricket program with mode:", mode, "profile:", profile, " args:", parsed_args)

    if mode == "sender" and profile == "sender_args_excel":
        parser2 = argparse.ArgumentParser()
        parser2.add_argument("-s", "--spreadsheet", required = True)
        parser2.add_argument("-w", "--worksheet", required = True)
        res = parser2.parse_args(additional_args)

    print(res)
    print(**res)
    res.__dict__.items()

    import time
    # import cricket_scorer.score_handlers.score_reader_i2c as reader
    import cricket_scorer.score_handlers.misc as m

    if mode == "sender":
        #  connection.sender_loop(params.sender_profiles[profile])
        print("Would now run with SENDER:", params.sender_profiles[profile])
        args = params.sender_profiles[profile]

        #  reader_gen = reader.score_reader_i2c(args.logger())
        reader_gen = m.score_generator(additional_args)

        coro = connection.sender_loop(args.logger(), args)
        await coro.asend(None)

        while True:
            score = next(reader_gen)
            print("Score is:", score)
            await coro.asend(score)
            time.sleep(1)

        #  i = 0
        #  while True:
            #  i += 1
            #  print("Main sending", i)
            #  val = await coro.asend(i)
            #  print("Main received", val, "\n")
            #  time.sleep(1)

    elif parsed_args.mode == "receiver":
        connection.receiver_loop(params.receiver_profiles[profile])

iol = asyncio.get_event_loop()
iol.run_until_complete(main())

#  if __name__ == "__main__":
    #  sys.exit(main(sys.argv))
