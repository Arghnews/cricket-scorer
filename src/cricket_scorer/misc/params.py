import copy
import collections
import inspect
import platform
import typing

from cricket_scorer.misc import my_logger
from cricket_scorer.net import udp_receive

from enum import Enum
Parameters = Enum("Parameters", "NOT_PROVIDED")

BuildFuncArgs = collections.namedtuple("BuildFuncArgs", ["func", "args"])

def add_helper(cls, name):
    add_name = "add_" + name
    assert not hasattr(cls, add_name)
    def f(self, value):
        self._simple_data[f.name] = value
        return self
    f.name = name
    setattr(cls, add_name, f)

def remove_prefix(string: str, prefix):
    assert string.startswith(prefix)
    return string[len(prefix):]

def get_method_name():
    return inspect.stack()[2][3]

def add_entry(profile_self, arg):
    name = remove_prefix(get_method_name(), "add_")
    assert name not in profile_self._simple_data
    profile_self._simple_data[name] = arg
    return profile_self

class BaseProfileBuilder:
    def __init__(self):
        self._simple_data = {}
        self._data: dict[str, BuildFuncArgs] = {}
    def add_logger(self, logger, logs_folder=None):
        assert logger in (my_logger.get_console_logger,
                my_logger.get_file_logger, my_logger.get_datetime_file_logger)
        d = {}
        if logger is not my_logger.get_console_logger:
            assert logs_folder is not None
            d["logs_folder"] = logs_folder
        self._data["logger"] = BuildFuncArgs(logger, d)
        return self
    def add_sock(self, port, host_ip_bind=Parameters.NOT_PROVIDED):
        d = {"server_port": port}
        if host_ip_bind is not Parameters.NOT_PROVIDED:
            d["host_ip_bind"] = host_ip_bind
        self._data["sock"] = BuildFuncArgs(udp_receive.SimpleUDP, d)
        return self

    def add_lookout_timeout_seconds(self, s):
        return add_entry(self, s)
    def add_receive_loop_timeout_milliseconds(self, t):
        return add_entry(self, t)

    def build(self, logs_folder=None):
        for k, v in self._simple_data.items():
            assert v is not None, f"Value must be supplied for key {k}"
        if logs_folder is not None:
            assert self._data["logger"].func is not my_logger.get_console_logger
            self._data["logger"].args["logs_folder"] = logs_folder
        return Args(self._simple_data, self._data)

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

class ReceiverProfileBuilder(BaseProfileBuilder):
    def __init__(self):
        super().__init__()
    def add_score_writer(self, writer):
        return add_entry(self, writer)

class Args:
    def __init__(self, simple_data: dict,
            data: typing.Dict[str, BuildFuncArgs]):
        self._data = data
        self._ready = simple_data

    def _get_logger(self):
        if "logger" not in self._ready:
            self._ready["logger"] = self._data["logger"].func(
                    **self._data["logger"].args)
        return self._ready["logger"]

    def _get_sock(self):
        if "sock" not in self._ready:
            self._ready["sock"] = self._data["sock"].func(self._get_logger(),
                    **self._data["sock"].args)
        return self._ready["sock"]

    def __getattr__(self, item):
        if item == "sock":
            return self._get_sock()
        elif item == "logger":
            return self._get_logger()
        elif item not in self._ready:
            raise AttributeError(f"No attribute {item}")
        return self._ready[item]

    def __str__(self):
        return str(self._ready) + "-" + str(self._data)

class Profiles:
    def __init__(self, profile_type_class):
        self._d: dict[str, BaseProfileBuilder] = {}
        self._profile_type_class = profile_type_class
        self._template_profiles = set()

    def get_profile_class(self):
        return self._profile_type_class()

    def get_buildable_profile_names(self):
        return [k for k in self._d.keys() if k not in self._template_profiles]

    def add_new(self, name, profile):
        assert name not in self._d, f"Profile \"{name}\" exists already"
        assert isinstance(profile, BaseProfileBuilder)
        self._d[name] = profile
        return self._profile_type_class()

    def _copy_and_update_dict(self, update_to, update_from):
        d = copy.deepcopy(update_to)
        d.update(update_from)
        return d

    def add_based_on(self, name, based_on, profile):
        assert based_on in self._d, f"Profile \"{based_on}\" must exist"
        assert isinstance(profile, BaseProfileBuilder)
        simple_data = self._copy_and_update_dict(self._d[based_on]._simple_data,
                profile._simple_data)
        data = self._copy_and_update_dict(self._d[based_on]._data,
                profile._data)
        profile._simple_data, profile._data = simple_data, data
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
        return profile.build(**kwargs)

        # Parameters.REQUIRED must be filled from kwargs -
        # Must use all params from kwargs
        # Must not be ambiguity
        # Overwriting of params

        #  duplicates = []
        #  for k, d in profile.items():
            #  single_param = len(d) == 1 and k in d
            #  if single_param:
                #  duplicates.append(k)
            #  else:
                #  duplicates.extend(k + "_" + kk for kk in d.keys())

        #  duplicates = {x for x in duplicates if duplicates.count(x) > 1}
        #  if duplicates:
            #  raise RuntimeError("Keys in a profile must be unique, multiple "
                    #  f"entries for: {duplicates}")

        #  d2 = {}
        #  for k, d in profile.items():
            #  print(k, d)
            #  single_param = len(d) == 1 and k in d
            #  not_provided_keys = []

            #  for kk, v in d.items():
                #  key = k + "_" + kk
                #  if key not in kwargs:
                    #  if v == Parameters.REQUIRED:
                        #  raise RuntimeError(f"Parameter {key} required but "
                                #  "not provided")
                    #  elif v == Parameters.NOT_PROVIDED:
                        #  not_provided_keys.append(kk)
                #  else:
                    #  print("waargh", kk, key)
                    #  d[kk] = kwargs[key]
                    #  print(d)
                    #  del kwargs[key]

            #  for kk in not_provided_keys:
                #  del d[kk]

            #  d2[k] = d
            #  if single_param:
                #  d2.update(d)
            #  else:
                #  if k == "logger":
                    #  print(d)
                    #  print("--")
                #  tup = namedtuple(k, d.keys())
                #  print("tup", tup)
                #  d2[k] = tup(**d)

        #  if len(kwargs) > 0:
            #  raise RuntimeError(f"Unused arguments: {kwargs}")

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

        #  return Args(**d2)
        #  return types.SimpleNamespace(**d2)

