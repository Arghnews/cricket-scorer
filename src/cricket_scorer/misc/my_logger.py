#!/usr/bin/env python3

import datetime
import logging
import os
import pathlib

# https://stackoverflow.com/a/39571473/8594193
# Make logger behave like print (ie. auto convert to string)
class LogWrapper():

    def __init__(self, logger):
        self.logger = logger

    def info(self, *args, sep=' '):
        self.logger.info(sep.join("{}".format(a) for a in args))

    def debug(self, *args, sep=' '):
        self.logger.debug(sep.join("{}".format(a) for a in args))

    def warning(self, *args, sep=' '):
        self.logger.warning(sep.join("{}".format(a) for a in args))

    def error(self, *args, sep=' '):
        self.logger.error(sep.join("{}".format(a) for a in args))

    def critical(self, *args, sep=' '):
        self.logger.critical(sep.join("{}".format(a) for a in args))

    def exception(self, *args, sep=' '):
        self.logger.exception(sep.join("{}".format(a) for a in args))

    def log(self, *args, sep=' '):
        self.logger.log(sep.join("{}".format(a) for a in args))

    def setLevel(self, *args):
        self.logger.setLevel(*args)

# Something to remember, we "may" run into a space issue with logfiles over
# time (seems unlikely but possible).
# Consider compressing old files. Take care to make a copy of an old logfile
# then "atomic" (as can be) mv them over etc. as we lose power via a hard reset
# whenever the board is switched off in practice, in a similar vein any
# streaming compression needs to consider this too (don't bother with it).

def get_console_logger():
    if not hasattr(get_console_logger, "logger"):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(get_console_handler())
        logger = LogWrapper(logger)
        get_console_logger.logger = logger
    return get_console_logger.logger

def get_file_logger(filename):
    # May want to add loggername parameter
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_console_handler())
    #  filename, verbose_filename = gen_logfile_name(filename)
    #  logger.addHandler(get_file_handler(filename, logging.INFO))
    logger.addHandler(get_file_handler(filename, logging.DEBUG))
    return LogWrapper(logger)

def get_datetime_file_logger(logs_folder):
    logfile_name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".log"
    pathlib.Path(logs_folder).mkdir(parents = True, exist_ok = True)
    logfile_path = os.path.join(logs_folder, logfile_name)
    return get_file_logger(logfile_path)

def get_formatter():
    # create formatter
    formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")
    return formatter

def get_console_handler():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(get_formatter())
    return console_handler

# eg. logging.INFO
def get_file_handler(filename, log_level):
    file_h = logging.FileHandler(filename)
    file_h.setLevel(log_level)
    file_h.setFormatter(get_formatter())
    return file_h

#  def get_console_and_file_logger(filename):
    #  # May want to add loggername parameter
    #  logger = logging.getLogger()
    #  logger.setLevel(logging.DEBUG)
    #  logger.addHandler(get_console_handler())
    #  filename, verbose_filename = gen_logfile_name(filename)
    #  logger.addHandler(get_file_handler(filename, logging.INFO))
    #  logger.addHandler(get_file_handler(verbose_filename, logging.DEBUG))
    #  return LogWrapper(logger)

#  def gen_logfile_name(filename):
    #  f = lambda f: ".".join([f, "verbose", "log"])
    #  return filename, f(filename[:-4] if filename.endswith(".log") else filename)

