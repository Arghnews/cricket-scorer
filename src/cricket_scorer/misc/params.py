import platform
import sys

from collections import namedtuple

excel_enabled = platform.system() == "Windows"
i2c_enabled = False

try:
    from smbus2 import SMBus
    i2c_enabled = True
except Exception:
    i2c_enabled = False

import cricket_scorer.score_handlers
from cricket_scorer.score_handlers import misc

if i2c_enabled:
    from cricket_scorer.score_handlers import (score_reader_i2c,
            score_writer_i2c_mark1, score_writer_i2c_mark2,
            score_writer_i2c_mark2_single_digit
            )

if excel_enabled:
    from cricket_scorer.score_handlers import (score_reader_excel)

from cricket_scorer.misc import my_logger
from cricket_scorer.net import udp_receive

# Directory where logfiles are stored, named by their starting datetime
logs_root = "/home/pi/cricket_scorer/logs"

ReceiverArgs = namedtuple("ReceiverArgs", [
    "lookout_timeout_seconds",
    "receive_loop_timeout_milliseconds",
    "score_writer",
    "logger",
    "sock",
    ])
SenderArgs = namedtuple("SenderArgs", [
    "receiver_ip_port",
    "lookout_timeout_seconds",
    "receive_loop_timeout_milliseconds",
    "new_connection_id_countdown_seconds",
    "last_received_timer_seconds",
    "resend_same_countdown_seconds",
    "score_reader",
    "logger",
    "sock",
    ])

sender_profiles = {}
receiver_profiles = {}

def assert_unique(name, profiles):
    if name in profiles:
        raise RuntimeError("Key " + name + "exists in profiles, keys must be "
                "unique")

def add_sender_profile(name, profile):
    assert_unique(name, sender_profiles)
    sender_profiles[name] = profile

def add_receiver_profile(name, profile):
    assert_unique(name, receiver_profiles)
    receiver_profiles[name] = profile

# Receiver configs

add_receiver_profile("test_receiver_args", ReceiverArgs(
    lookout_timeout_seconds = 10,
    receive_loop_timeout_milliseconds = 5000,
    score_writer = misc.ScorePrinter,
    logger = my_logger.get_console_logger,
    sock = lambda logger: udp_receive.SimpleUDP(2520, logger),
    ))

if i2c_enabled:
    add_receiver_profile("receiver_args_mark2", ReceiverArgs(
        lookout_timeout_seconds = 20,
        receive_loop_timeout_milliseconds = 5000,
        score_writer = score_writer_i2c_mark2.ScoreWriterI2cMark2,
        logger = lambda: my_logger.get_datetime_file_logger(logs_root = logs_root),
        sock = lambda logger: udp_receive.SimpleUDP(2520, logger),
        ))

    add_receiver_profile("receiver_args_mark1",
            receiver_profiles["receiver_args_mark2"]._replace(
        score_writer = score_writer_i2c_mark1.ScoreWriterI2cMark1,
        ))

    add_receiver_profile("test_receiver_args_mark1",
            receiver_profiles["receiver_args_mark1"]._replace(
        logger = my_logger.get_console_logger,
        ))

    add_receiver_profile("test_receiver_args_mark2",
            receiver_profiles["receiver_args_mark2"]._replace(
        logger = my_logger.get_console_logger,
        ))

    add_receiver_profile("test_receiver_args_live_single_digit",
            receiver_profiles["receiver_args_mark2"]._replace(
        score_writer = score_writer_i2c_mark2_single_digit.ScoreWriterI2cSingleDigit,
        ))

# Sender configs

add_sender_profile("test_sender_args", SenderArgs(
    receiver_ip_port = ("127.0.0.1", 2520),
    lookout_timeout_seconds = 10,
    receive_loop_timeout_milliseconds = 3000,
    new_connection_id_countdown_seconds = 10,
    last_received_timer_seconds = 25,
    resend_same_countdown_seconds = 0.35,
    score_reader = misc.ScoreGenerator,
    logger = my_logger.get_console_logger,
    sock = lambda logger: udp_receive.SimpleUDP(2521, logger),
    ))

add_sender_profile("test_sender_args_ethernet",
        sender_profiles["test_sender_args"]._replace(
    sock = lambda logger: udp_receive.SimpleUDP(2521, logger, "192.168.1.23")
    ))

add_sender_profile("test_sender_args_wifi",
        sender_profiles["test_sender_args"]._replace(
    sock = lambda logger: udp_receive.SimpleUDP(2521, logger, "192.168.1.22")
    ))

# Not meant to be instantiated itself
add_sender_profile("_sender_args_base", SenderArgs(
    receiver_ip_port = ("192.168.4.1", 2520),
    lookout_timeout_seconds = 10,
    receive_loop_timeout_milliseconds = 2000,
    new_connection_id_countdown_seconds = 10,
    last_received_timer_seconds = 45,
    resend_same_countdown_seconds = 0.5,
    score_reader = None,
    logger = lambda: my_logger.get_datetime_file_logger(logs_root = logs_root),
    sock = lambda logger: udp_receive.SimpleUDP(2521, logger),
    ))

if i2c_enabled:
    add_sender_profile("sender_args_i2c",
            sender_profiles["_sender_args_base"]._replace(
        score_reader = score_reader_i2c.ScoreReaderI2c,
        logger = lambda: my_logger.get_datetime_file_logger(logs_root = logs_root),
        ))

    add_sender_profile("test_sender_args_i2c",
            sender_profiles["sender_args_i2c"]._replace(
        logger = my_logger.get_console_logger,
        ))

if excel_enabled:
    add_sender_profile("sender_args_excel",
            sender_profiles["_sender_args_base"]._replace(
        logger = my_logger.get_console_logger,
        score_reader = score_reader_excel.ScoreReaderExcel,
        ))
