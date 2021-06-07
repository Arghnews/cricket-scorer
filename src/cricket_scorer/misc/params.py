import copy
import inspect
import platform
import sys
import types

from collections import namedtuple

#  excel_enabled = platform.system() == "Windows"
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

#  if excel_enabled:
    #  from cricket_scorer.score_handlers import (score_reader_excel)

from cricket_scorer.misc import my_logger
from cricket_scorer.net import udp_receive

from enum import Enum
# TODO: handle NOT_PROVIDED for host_ip_bind in the build_profile method
# And consider/handle what must be done on build_based_on etc. methods
Parameters = Enum("Parameters", "REQUIRED NOT_PROVIDED")

def remove_prefix(string: str, prefix):
    assert string.startswith(prefix)
    return string[len(prefix):]

def get_method_name():
    return inspect.stack()[2][3]

def add_entry(profile_self, arg, **kwargs):
    name = remove_prefix(get_method_name(), "add_")
    assert name not in profile_self._d
    assert name not in kwargs
    profile_self._d[name] = {name: arg}
    profile_self._d[name].update(kwargs)
    return profile_self

# TODO: move this all to it's own file obviously

class BaseProfileBuilder:
    def __init__(self):
        self._d = {}
    def add_lookout_timeout_seconds(self, s):
        return add_entry(self, s)
    def add_logger(self, logger, logs_folder=None):
        if logger is my_logger.get_console_logger:
            assert logs_folder is None
        return add_entry(self, logger, logs_folder=logs_folder)
    def add_sock(self, port, host_ip_bind=Parameters.NOT_PROVIDED):
        return add_entry(self, udp_receive.SimpleUDP, port=port,
                sock_host_ip_bind=host_ip_bind)
    def add_receive_loop_timeout_milliseconds(self, t):
        return add_entry(self, t)

class SenderProfileBuilder(BaseProfileBuilder):
    def __init__(self):
        super().__init__()
    def add_receiver_ip_port(self, ip_port):
        return add_entry(self, ip_port)
    def add_score_reader(self, reader):
        return add_entry(self, reader)
    def add_new_connection_id_countdown_seconds(self, s):
        return add_entry(self, s)
    def add_last_received_timer_seconds(self, s):
        return add_entry(self, s)
    def add_resend_same_countdown_seconds(self, s):
        return add_entry(self, s)

assert isinstance(SenderProfileBuilder(), BaseProfileBuilder), ""

class ReceiverProfileBuilder(BaseProfileBuilder):
    def __init__(self):
        super().__init__()
    def add_score_writer(self, writer):
        return add_entry(self, writer)

#  class Args:
    #  def __init__(self, d):
        #  self._log_ready = False
        #  self._data = {
                #  "log": d["logger"],
                #  "logs_folder": None,
                #  }

    #  @property
    #  def log(self):
        #  if not self._log_ready:
            #  self._log_ready = True

# TODO: neat way to add template profiles that can't be instantiated but added
# based on them
class Profiles:
    def __init__(self, profile_type_class):
        self._d: dict[str, dict] = {}
        self._profile_type_class = profile_type_class
        self._template_profiles = set()

    def get_profile_class(self):
        return self._profile_type_class()

    def get_buildable_profile_names(self):
        return [k for k in self._d.keys() if k not in self._template_profiles]

    def add_new(self, name, profile):
        assert name not in self._d, f"Profile \"{name}\" exists already"
        assert isinstance(profile, BaseProfileBuilder)
        self._d[name] = profile._d
        return self._profile_type_class()

    def add_based_on(self, name, based_on, profile):
        assert based_on in self._d, f"Profile \"{based_on}\" must exist"
        assert isinstance(profile, BaseProfileBuilder)
        base_profile_dict = copy.deepcopy(self._d[based_on])
        base_profile_dict.update(profile._d)
        profile._d = base_profile_dict
        return self.add_new(name, profile)

    def add_new_template(self, name, profile):
        """A template profile cannot itself be built, only other profiles 
        built based on it"""
        self._template_profiles.add(name)
        return self.add_new(name, profile)

    def build_profile(self, name, **kwargs):
        if name in self._template_profiles:
            raise RuntimeError(f"Cannot build profile \"{name}\" as it's a "
                    "template profile, only other profiles may be based off it")

        profile = self._d[name]
        print("Profile dict:", profile)

        # Parameters.REQUIRED must be filled from kwargs -
        # Must use all params from kwargs
        # Must not be ambiguity
        # Overwriting of params

        duplicates = []
        for k, d in profile.items():
            single_param = len(d) == 1 and k in d
            if single_param:
                duplicates.append(k)
            else:
                duplicates.extend(k + "_" + kk for kk in d.keys())

        duplicates = {x for x in duplicates if duplicates.count(x) > 1}
        if duplicates:
            raise RuntimeError("Keys in a profile must be unique, multiple "
                    f"entries for: {duplicates}")

        d2 = {}
        for k, d in profile.items():
            print(k, d)
            single_param = len(d) == 1 and k in d
            not_provided_keys = []

            for kk, v in d.items():
                key = k + "_" + kk
                if key not in kwargs:
                    if v == Parameters.REQUIRED:
                        raise RuntimeError(f"Parameter {key} required but "
                                "not provided")
                    elif v == Parameters.NOT_PROVIDED:
                        not_provided_keys.append(kk)
                else:
                    print("waargh", kk, key)
                    d[kk] = kwargs[key]
                    print(d)
                    del kwargs[key]

            for kk in not_provided_keys:
                del d[kk]

            if single_param:
                d2.update(d)
            else:
                if k == "logger":
                    print(d)
                    print("--")
                tup = namedtuple(k, d.keys())
                print("tup", tup)
                d2[k] = tup(**d)

        if len(kwargs) > 0:
            raise RuntimeError(f"Unused arguments: {kwargs}")

        #  print(d2)
        #  assert False

        #  required_params = {k for k, v in dd.items() if v is Parameters.REQUIRED}
        #  given_params = set(kwargs.keys())

        #  missing_params = required_params - given_params
        #  redundant_params = given_params - required_params

        #  if missing_params:
            #  raise RuntimeError(f"These parameters must be specified: "
                    #  f"{missing_params}")

        #  if redundant_params:
            #  raise RuntimeError(f"Redundant extra parameters: "
                    #  f"{redundant_params}")

        #  for k in [k for k, v in dd.items() if v == Parameters.NOT_PROVIDED]:
            #  del dd[k]

        return types.SimpleNamespace(**d2)

sender_profiles = Profiles(SenderProfileBuilder)
receiver_profiles = Profiles(ReceiverProfileBuilder)

logs_folder_raspberry_pi = "/home/pi/cricket_scorer/logs"

receiver_profiles.add_new("test_receiver_args",
        receiver_profiles.get_profile_class()
        .add_lookout_timeout_seconds(10)
        .add_receive_loop_timeout_milliseconds(5000)
        .add_score_writer(misc.ScorePrinter)
        .add_logger(my_logger.get_console_logger)
        .add_sock(2521)
        )

if i2c_enabled:
    receiver_profiles.add_new("receiver_args_mark2",
            receiver_profiles.get_profile_class()
            .add_lookout_timeout_seconds(20)
            .add_receive_loop_timeout_milliseconds(5000)
            .add_score_writer(score_writer_i2c_mark2.ScoreWriterI2cMark2)
            .add_logger(my_logger.get_datetime_file_logger,
                logs_folder=logs_folder_raspberry_pi)
            .add_sock(2520)
            )

    receiver_profiles.add_based_on("receiver_args_mark1", "receiver_args_mark2",
            receiver_profiles.get_profile_class()
            .add_score_writer(score_writer_i2c_mark1.ScoreWriterI2cMark1)
            )

    receiver_profiles.add_based_on("test_receiver_args_mark1",
            "receiver_args_mark1",
            receiver_profiles.get_profile_class()
            .add_logger(my_logger.get_console_logger)
            )

    receiver_profiles.add_based_on("test_receiver_args_mark2",
            "receiver_args_mark2",
            receiver_profiles.get_profile_class()
            .add_logger(my_logger.get_console_logger)
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
        .add_receiver_ip_port(("127.0.0.1", 2520))
        .add_lookout_timeout_seconds(10)
        .add_receive_loop_timeout_milliseconds(3000)
        .add_new_connection_id_countdown_seconds(10)
        .add_last_received_timer_seconds(25)
        .add_resend_same_countdown_seconds(0.35)
        .add_score_reader(misc.score_generator)
        .add_logger(my_logger.get_console_logger)
        .add_sock(2521)
        )

sender_profiles.add_based_on("test_sender_args_ethernet", "test_sender_args",
        sender_profiles.get_profile_class()
        .add_sock(port=2521, host_ip_bind="192.168.1.23")
        )

sender_profiles.add_based_on("test_sender_args_wifi", "test_sender_args",
        sender_profiles.get_profile_class()
        .add_sock(port=2521, host_ip_bind="192.168.1.22")
        )

sender_profiles.add_new_template("sender_args_base",
        sender_profiles.get_profile_class()
        .add_receiver_ip_port(("192.168.4.1", 2520))
        .add_lookout_timeout_seconds(10)
        .add_receive_loop_timeout_milliseconds(2000)
        .add_new_connection_id_countdown_seconds(10)
        .add_last_received_timer_seconds(45)
        .add_resend_same_countdown_seconds(0.5)
        .add_score_reader(Parameters.REQUIRED)
        .add_logger(my_logger.get_datetime_file_logger,
            logs_folder=logs_folder_raspberry_pi)
        .add_sock(2521)
        )

if i2c_enabled:
    sender_profiles.add_based_on("sender_args_i2c", "sender_args_base",
            sender_profiles.get_profile_class()
            .add_score_reader(score_reader_i2c.score_reader_i2c)
            )

    sender_profiles.add_based_on("test_sender_args_i2c", "sender_args_i2c",
            sender_profiles.get_profile_class()
            .add_logger(my_logger.get_console_logger)
            )

#  #  TODO: this probably shouldn't be a console logger only in actual
#  if excel_enabled:
    #  add_sender_profile("sender_args_excel",
           #  sender_profiles["_sender_args_base"]._replace(
       #  score_reader = lambda *args, **kwargs: score_reader_excel.score_reader_excel(*args, **kwargs),
       #  ))
    #  add_sender_profile("sender_args_excel", SenderArgs(
        #  receiver_ip_port = ("192.168.4.1", 2520),
        #  lookout_timeout_seconds = 10,
        #  receive_loop_timeout_milliseconds = 20,
        #  new_connection_id_countdown_seconds = 10,
        #  last_received_timer_seconds = 45,
        #  resend_same_countdown_seconds = 0.5,
        #  # score_reader = None,
        #  score_reader = lambda *args, **kwargs: score_reader_excel.score_reader_excel(
            #  *args, **kwargs),
        #  # logger = lambda: my_logger.get_datetime_file_logger(logs_root = logs_root),
        #  logger = my_logger.get_console_logger,
        #  sock = lambda logger: udp_receive.SimpleUDP(2521, logger),
        #  ))

