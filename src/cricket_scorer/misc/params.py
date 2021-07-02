import copy
import collections
import inspect
import typing

from cricket_scorer.misc import my_logger
from cricket_scorer.net import udp_receive

from enum import Enum

Parameters = Enum("Parameters", "NOT_PROVIDED")

BuildFuncArgs = collections.namedtuple("BuildFuncArgs", ["func", "args"])


def _remove_prefix(string: str, prefix):
    assert string.startswith(prefix)
    return string[len(prefix):]


def _get_method_name():
    """Helper to pull X from add_X calling method"""
    return inspect.stack()[2][3]


def _add_entry(profile_self, arg):
    """Helper to add argument to a profile based on the calling method's name"""
    name = _remove_prefix(_get_method_name(), "add_")
    assert name not in profile_self._simple_data
    profile_self._simple_data[name] = arg
    return profile_self


class BaseProfileBuilder:
    def __init__(self):
        self._simple_data = {}
        self._data: dict[str, typing.Union[ArgWrapper, None]] = {}

    def add_logs_folder(self, logs_folder=None, overwrite_if_none=False):
        if logs_folder == "":
            raise RuntimeError("Logs folder cannot be empty string")
        if logs_folder is None and overwrite_if_none:
            self._data["logger"] = None
        if logs_folder is not None:
            self._data["logger"] = ArgWrapper(
                BuildFuncArgs(my_logger.add_datetime_file_handler, {"logs_folder": logs_folder}),
                closing_func=lambda _: my_logger.close_file_handler())
        return self

    def add_sock(self, port, host_ip_bind=Parameters.NOT_PROVIDED):
        d = {"server_port": port}
        if host_ip_bind is not Parameters.NOT_PROVIDED:
            d["host_ip_bind"] = host_ip_bind
        self._data["sock"] = ArgWrapper(BuildFuncArgs(udp_receive.SimpleUDP, d),
                                        closing_func=lambda sock: sock.close(),
                                        depends_on_logger=True)
        return self

    def add_lookout_timeout_seconds(self, s):
        """When on and not connected, occasionally send out messages to the
        receiver in case it's come up to alert it that we're switched on."""
        return _add_entry(self, s)

    def add_receive_loop_timeout_milliseconds(self, t):
        """Amount of time the socket will block and listen for network
        messages."""
        return _add_entry(self, t)


def _build_profile(profile: BaseProfileBuilder, logs_folder=None, overwrite_if_none=False):
    # Don't mutate the profile object itself, ie. should be able to build the profile
    # as many times as you like without it changing.
    profile = copy.deepcopy(profile)

    profile.add_logs_folder(logs_folder, overwrite_if_none)

    if "logger" not in profile._data or profile._data["logger"] is None:
        profile._data["logger"] = ArgWrapper(value=my_logger.get_logger(), is_initialised=True)

    assert None not in profile._data.values()

    for k, v in profile._simple_data.items():
        assert v is not None, f"Value must be supplied for key {k}"

    data = {
        k: ArgWrapper(value=v, is_initialised=True)
        for k, v in copy.deepcopy(profile._simple_data).items()
    }
    assert all(isinstance(v, ArgWrapper) for v in data.values())
    data.update(copy.deepcopy(profile._data))

    return Args(data)


class SenderProfileBuilder(BaseProfileBuilder):
    def __init__(self):
        super().__init__()
        # Don't be tempted to put a line like this here
        # self._data["score_reader"] = None
        # If this profile is added based on another, this None line will overwrite
        # a potentially otherwise valid variable
    def add_receiver_ip_port(self, ip_port):
        return _add_entry(self, ip_port)

    def add_score_reader(self, reader):
        self._data["score_reader"] = ArgWrapper(BuildFuncArgs(reader, {}),
                                                closing_func=lambda reader: reader.close(),
                                                depends_on_logger=True)
        return self

    def add_new_connection_id_countdown_seconds(self, s):
        """Timer from when receive message from new client. If don't get a
        response within this timeout, will assume the client is switched off
        or we received an old message."""
        return _add_entry(self, s)

    def add_last_received_timer_seconds(self, s):
        """When connected, there can be periods of little to no network
        activity. The receiver/client should ping this sender box with lookout
        messages to confirm it's still there, ie. it hasn't been switched off.
        This is the timeout for how long to wait until receiving one of those
        messages before assuming the remote end is switched off and
        disconnecting. This should therefore be realistically at least double
        the lookout_timeout on the receiver."""
        return _add_entry(self, s)

    def add_resend_same_countdown_seconds(self, s):
        """We use this to avoid resending the same score again in a short amount
        of time."""
        return _add_entry(self, s)


class ReceiverProfileBuilder(BaseProfileBuilder):
    def __init__(self):
        super().__init__()

    def add_score_writer(self, writer):
        self._data["score_writer"] = ArgWrapper(BuildFuncArgs(writer, {}), depends_on_logger=True)
        return self


class ArgWrapper:
    """Class that holds either a pre-initialised argument like an int, or
    something more complicated that can supply callbacks for initialisation and
    closing.

    """
    def __init__(self,
                 builder_func=None,
                 value=None,
                 *,
                 is_initialised=False,
                 closing_func=None,
                 depends_on_logger=False) -> None:
        pre_ready = builder_func is None and is_initialised and value is not None
        needs_to_build = builder_func is not None and not is_initialised \
            and value is None
        assert pre_ready ^ needs_to_build
        if is_initialised:
            assert not depends_on_logger

        self._pre_ready = is_initialised
        self._is_initialised = is_initialised
        self._builder_func = builder_func
        self._value = value
        self._closing_func = closing_func
        self._depends_on_logger = depends_on_logger

    def initialise(self, logger=None):
        if self._pre_ready or self.is_initialised():
            return
        if self._depends_on_logger:
            self._value = self._builder_func.func(logger, **self._builder_func.args)
        else:
            # print(self._builder_func)
            # print(self._builder_func.args)
            self._value = self._builder_func.func(**self._builder_func.args)
        self._is_initialised = True

    def is_initialised(self):
        return self._is_initialised

    def value(self):
        # TODO: consider changing to property
        assert self.is_initialised()
        return self._value

    def is_pre_ready(self):
        return self._pre_ready

    def close(self):
        if self.is_initialised() and self._closing_func is not None:
            self._closing_func(self._value)

    def __str__(self) -> str:
        if self._pre_ready:
            return str(self.value())
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)


class Args:
    """Class to abstract away parameters and their initialisation/closing.
    Should not be instantiated directly but return from a
    BaseProfileBuilder.build_profile() type call.
    Has context manager support.

    # Example usage
    from cricket_scorer.misc.profiles import SENDER_PROFILES
    args: Args = SENDER_PROFILES.build_profile("test_profile_1")
    args.init_all() # 2 stage initialisation, for exception catching/handling
    args.logger.info("bla")
    print(args.lookout_timeout_seconds)
    args.close()
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def close(self):
        """Close everything, closes (detaches any handlers set by this) the
        logger last. Must not throw.
        """
        assert not self._is_closed, "Args .close() called twice"
        self._is_closed = True

        if self._data["logger"].is_initialised():
            log = self.logger
        else:
            # Dislike having a global-esque dependency, but works
            log = my_logger.get_logger()
        for k, v in reversed([(k, v) for k, v in self._data.items() if k != "logger"]):
            if not v.is_pre_ready():
                log.debug(f"Closing {k}: {v}")
            try:
                v.close()
            except Exception as e:
                log.error(f"Error {e} occured while closing {k}: {v}")
        self._data["logger"].close()

    def __del__(self):
        if not self._is_closed:
            my_logger.get_logger().warning("Args destructor called but close hasn't been")

    def __init__(self, data: typing.Dict[str, ArgWrapper]):
        self._is_closed = False
        self._data = data

    def init_logger(self):
        self._data["logger"].initialise()

    # Needs to be split out like this as one thing we may initialise is the socket
    # which may throw. We want the logger initialised first so can record that event
    # in the log
    def init_all(self):
        """Must be called prior to using this. May throw"""
        self.init_logger()
        log = self.logger
        for k, v in [(k, v) for k, v in self._data.items() if k != "logger"]:
            if not v.is_initialised():
                log.debug(f"Initialising {k}: {v}")
                v.initialise(log)
            else:
                log.debug(f"{k} already initialised, doing nothing")

    def __getattr__(self, item):
        if item in self._data:
            return self._data[item].value()
        raise AttributeError(f"No attribute {item}")

    def __str__(self):
        return "".join(f"{k}: {v}\n" for k, v in self._data.items())


class Profiles:
    """Holds and builds profiles"""
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
        data = self._copy_and_update_dict(self._d[based_on]._data, profile._data)
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

        if name not in self.get_buildable_profile_names():
            raise RuntimeError(f"Profile {name} does not exist, choose from: "
                               f"{self.get_buildable_profile_names()}")

        profile = self._d[name]
        return _build_profile(profile, **kwargs)
