#!/usr/bin/env python3

import datetime
import logging
import os
import pathlib

# https://stackoverflow.com/a/39571473/8594193
# Make logger behave like print (ie. auto convert to string)
class LogWrapper(logging.Logger):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._file_handler = None

    def info(self, *args, sep=' '):
        super().info(sep.join("{}".format(a) for a in args))

    def debug(self, *args, sep=' '):
        super().debug(sep.join("{}".format(a) for a in args))

    def warning(self, *args, sep=' '):
        super().warning(sep.join("{}".format(a) for a in args))

    def error(self, *args, sep=' '):
        super().error(sep.join("{}".format(a) for a in args))

    def critical(self, *args, sep=' '):
        super().critical(sep.join("{}".format(a) for a in args))

    def exception(self, *args, sep=' '):
        super().exception(sep.join("{}".format(a) for a in args))

    def log(self, *args, sep=' '):
        super().log(sep.join("{}".format(a) for a in args))

    def enable_datetime_file_logging(self, logs_folder):
        assert logs_folder is not None
        logfile_name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log"
        pathlib.Path(logs_folder).mkdir(parents = True, exist_ok = True)
        filename = os.path.join(logs_folder, logfile_name)

        file_h = logging.FileHandler(filename)
        file_h.set_name(filename)
        file_h.setLevel(logging.DEBUG)
        file_h.setFormatter(get_formatter())

        assert self._file_handler is None
        self._file_handler = file_h
        self.addHandler(file_h)
        return self

    def close_datetime_file(self):
        assert self._file_handler is not None
        self._file_handler.close()
        self.removeHandler(self._file_handler)
        self._file_handler = None

# Something to remember, we "may" run into a space issue with logfiles over
# time (seems unlikely but possible).
# Consider compressing old files. Take care to make a copy of an old logfile
# then "atomic" (as can be) mv them over etc. as we lose power via a hard reset
# whenever the board is switched off in practice, in a similar vein any
# streaming compression needs to consider this too (don't bother with it).

_LOGGER_NAME = "log"

def get_logger():
    return logging.getLogger(_LOGGER_NAME)

def get_console_logger():
    return logging.getLogger(_LOGGER_NAME)

def get_datetime_file_logger(logs_folder):
    logfile_name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log"
    pathlib.Path(logs_folder).mkdir(parents = True, exist_ok = True)
    logfile_path = os.path.join(logs_folder, logfile_name)
    return _get_file_logger(logfile_path)

# def close_file_handler(logger, handler):
#     logger.removeHandler(handler)

# def make_close_file_handler(logger, handler):
#     pass

def _get_file_logger(filename):
    logger = logging.getLogger(_LOGGER_NAME)

    # For now, can assume only one file handler is present at once
    file_handlers = [h for h in logger.handlers if isinstance(
        h, logging.FileHandler)]

    assert len(file_handlers) == 0, f"May only get one file handler when none registered"

    return logger

def get_formatter():
    # create formatter
    formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")
    return formatter

def _get_console_handler(level=logging.DEBUG):
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(get_formatter())
    return console_handler

# eg. logging.INFO
def _get_file_handler(filename, level=logging.DEBUG):
    file_h = logging.FileHandler(filename)
    file_h.set_name(filename)
    file_h.setLevel(level)
    file_h.setFormatter(get_formatter())
    return file_h

logging.setLoggerClass(LogWrapper)
_logger = logging.getLogger(_LOGGER_NAME)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_get_console_handler())
