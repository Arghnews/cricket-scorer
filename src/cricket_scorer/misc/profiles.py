from . import params

import cricket_scorer.misc.my_platform as my_platform

from cricket_scorer.score_handlers import misc

if my_platform.I2C_ENABLED:
    from cricket_scorer.score_handlers import (score_reader_i2c,
            score_writer_i2c_mark1, score_writer_i2c_mark2,
            score_writer_i2c_mark2_single_digit
            )

from cricket_scorer.score_handlers import score_reader_excel_dummy
if my_platform.EXCEL_ENABLED:
    from cricket_scorer.score_handlers import score_reader_excel

sender_profiles = params.Profiles(params.SenderProfileBuilder)
receiver_profiles = params.Profiles(params.ReceiverProfileBuilder)

LOGS_FOLDER_RASPBERRY_PI = "/home/pi/cricket_scorer/logs"
RECEIVER_LISTEN_PORT = 2520
RECEIVER_IP = "192.168.4.1"

# Relatively unimportant as receiver responds to sender address including port
SENDER_LISTEN_PORT = 2521

receiver_profiles.add_new_template("receiver_args_base",
        receiver_profiles.get_profile_class()
        .add_receive_loop_timeout_milliseconds(5000)
        .add_sock(RECEIVER_LISTEN_PORT)
        )

receiver_profiles.add_based_on("test_receiver_args", "receiver_args_base",
        receiver_profiles.get_profile_class()
        .add_lookout_timeout_seconds(10)
        .add_score_writer(misc.ScorePrinter)
        )

if my_platform.I2C_ENABLED:
    receiver_profiles.add_based_on("receiver_args_mark2", "receiver_args_base",
            receiver_profiles.get_profile_class()
            .add_lookout_timeout_seconds(20)
            .add_score_writer(score_writer_i2c_mark2.ScoreWriterI2cMark2)
            .add_logs_folder(LOGS_FOLDER_RASPBERRY_PI)
            )

    receiver_profiles.add_based_on("receiver_args_mark1", "receiver_args_mark2",
            receiver_profiles.get_profile_class()
            .add_score_writer(score_writer_i2c_mark1.ScoreWriterI2cMark1)
            )

    receiver_profiles.add_based_on("test_receiver_args_mark1",
            "receiver_args_mark1",
            receiver_profiles.get_profile_class()
            .add_logs_folder(None, overwrite_if_none=True)
            )

    receiver_profiles.add_based_on("test_receiver_args_mark2",
            "receiver_args_mark2",
            receiver_profiles.get_profile_class()
            .add_logs_folder(None, overwrite_if_none=True)
            )

    receiver_profiles.add_based_on("test_receiver_args_live_single_digit",
            "receiver_args_mark2",
            receiver_profiles.get_profile_class()
            .add_score_writer(
                score_writer_i2c_mark2_single_digit.ScoreWriterI2cSingleDigit)
            )

# Sender configs

sender_profiles.add_new("test_sender_args",
        sender_profiles.get_profile_class()
        .add_receiver_ip_port(("127.0.0.1", RECEIVER_LISTEN_PORT))
        .add_lookout_timeout_seconds(10)
        .add_receive_loop_timeout_milliseconds(3000)
        .add_new_connection_id_countdown_seconds(10)
        .add_last_received_timer_seconds(25)
        .add_resend_same_countdown_seconds(0.35)
        .add_score_reader(misc.ScoreGenerator)
        .add_sock(SENDER_LISTEN_PORT)
        )

sender_profiles.add_based_on("test_sender_args_ethernet", "test_sender_args",
        sender_profiles.get_profile_class()
        .add_sock(port=SENDER_LISTEN_PORT, host_ip_bind="192.168.1.23")
        )

sender_profiles.add_based_on("test_sender_args_wifi", "test_sender_args",
        sender_profiles.get_profile_class()
        .add_sock(port=SENDER_LISTEN_PORT, host_ip_bind="192.168.1.22")
        )

sender_profiles.add_new_template("sender_args_base",
        sender_profiles.get_profile_class()
        .add_receiver_ip_port((RECEIVER_IP, RECEIVER_LISTEN_PORT))
        .add_lookout_timeout_seconds(10)
        .add_receive_loop_timeout_milliseconds(2000)
        .add_new_connection_id_countdown_seconds(10)
        .add_last_received_timer_seconds(45)
        .add_resend_same_countdown_seconds(0.5)
        .add_score_reader(None)
        .add_sock(SENDER_LISTEN_PORT)
        )

if my_platform.I2C_ENABLED:
    sender_profiles.add_based_on("sender_args_i2c", "sender_args_base",
            sender_profiles.get_profile_class()
            .add_score_reader(score_reader_i2c.ScoreReaderI2c)
            .add_logs_folder(LOGS_FOLDER_RASPBERRY_PI)
            )

    sender_profiles.add_based_on("test_sender_args_i2c", "sender_args_i2c",
            sender_profiles.get_profile_class()
            )

#  TODO: this probably shouldn't be a console logger only in actual

sender_profiles.add_based_on("test_sender_args_excel", "sender_args_base",
        sender_profiles.get_profile_class()
        .add_receiver_ip_port(("127.0.0.1", RECEIVER_LISTEN_PORT))
        .add_receive_loop_timeout_milliseconds(0)
        .add_last_received_timer_seconds(35)
        .add_score_reader(score_reader_excel_dummy.get_score_reader)
        )

sender_profiles.add_based_on("test_sender_args_excel_remote_ip", "test_sender_args_excel",
        sender_profiles.get_profile_class()
        .add_receiver_ip_port((RECEIVER_IP, RECEIVER_LISTEN_PORT))
        )

if my_platform.EXCEL_ENABLED:
        sender_profiles.add_based_on("test_sender_args_actual_excel", "test_sender_args_excel",
                sender_profiles.get_profile_class()
                .add_score_reader(score_reader_excel.get_score_reader)
                )
