#!/usr/bin/env python3

import atexit
import copy
import functools
import importlib.resources
import io
import logging
import multiprocessing
import os
import pathlib
import platform
import sys
import textwrap
import time
import traceback
import types
import typing
from winreg import SetValue

import PySimpleGUI as sg
import plyer

from cricket_scorer.misc import my_logger, profiles
from cricket_scorer.misc.params import Args
from cricket_scorer.misc.profiles import RECEIVER_WIFI_SSID, RECEIVER_WIFI_PASSWORD
from cricket_scorer.net import connection
from cricket_scorer.net.countdown_timer import make_countdown_timer
from cricket_scorer.score_handlers.scoredata import ScoreData

# class OnlyPrintOnDiff:
#     def __init__(self):
#         self.buf = io.StringIO()
#         self.prev = None

#     def print(self, *args, **kwargs):
#         print(*args, file=self.buf, **kwargs)

#     def print_contents_if_diff(self):
#         contents = self.buf.getvalue()

#         if contents != self.prev:
#             print(contents, end="")

#         self.prev = contents
#         self.buf = io.StringIO()


class BetterTimer:
    """Grouping of timers by name to measure restartable performance timing of
    segments of code
    """

    def __init__(self) -> None:
        self._timers = {}

    # def restart(self):
    #     self._timers.clear()

    def start(self, name):
        total, started = self._timers.setdefault(name, (0, -1))
        assert started == -1, "Must be stopped before starting"
        self._timers[name] = (total, time.time())

    def stop(self, name):
        assert name in self._timers
        total, started = self._timers.get(name)
        assert started != -1, "Must be started before stopped"
        total += time.time() - started
        self._timers[name] = (total, -1)

    def running(self, name):
        return name in self._timers and self._timers[name][1] != -1

    def summary(self):
        for k in self._timers:
            if self.running(k):
                self.stop(k)
        return [f"{name} -> {t}" for name, (t, _) in self._timers.items()]


class MyLogFilter(logging.Filter):
    """Log filter attached to the handler for the logs tab in the GUI. The
    setLevel method is called to change the level that is displayed.
    """

    def __init__(self) -> None:
        super().__init__()
        self._level = 0

    def filter(self, record: logging.LogRecord) -> int:
        return record.levelno >= self._level

    def setLevel(self, level: str):
        assert hasattr(logging, level.upper()
                       ), f"Log level {level} does not exist"
        self._level = getattr(logging, level.upper())


def get_resources():
    # https://pyinstaller.readthedocs.io/en/stable/runtime-information.html

    data = types.SimpleNamespace()

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle

        # https://pyinstaller.readthedocs.io/en/stable/runtime-information.html
        # Load resources like licenses as per pyinstaller docs

        def join_text_to_license(text, license):
            return ("\n\n" + "-" * 20 + "\n\n").join((text, license))

        data.name_to_license = {}

        # Root directory
        root = (pathlib.Path.cwd() / __file__).parents[0]

        # Add 3rd party licenses
        licenses_folder = root.joinpath("cricket_scorer/data/licenses")
        assert licenses_folder.exists()
        for license_dir in licenses_folder.iterdir():
            license_for = license_dir.name
            text_file, license_file = license_dir / \
                "header.txt", license_dir / "LICENSE.txt"
            text, license = text_file.read_text(), license_file.read_text()
            data.name_to_license[license_for] = join_text_to_license(
                text, license)

        data.icon_path = root.joinpath("cricket_scorer/data/icons/cricket.ico")
        assert data.icon_path.exists()

        with open(root.joinpath("version.txt"), "r") as f:
            data.version = f.read()

    else:
        root = "cricket_scorer.data"
        package = ".".join((root, "licenses"))
        data.name_to_license = {}
        for license_dir in importlib.resources.contents(package):
            # print(license_dir)
            if license_dir.startswith("__"):
                continue
            subpackage = ".".join((package, license_dir))
            header = importlib.resources.read_text(subpackage, "header.txt")
            license = importlib.resources.read_text(subpackage, "LICENSE.txt")
            data.name_to_license[license_dir] = "\n\n\n\n".join(
                (header, license))
        fp = importlib.resources.path(".".join((root, "icons")), "cricket.ico")
        # plyer requires an ico filepath, it only reads from the file anyway so
        # shouldn't be an issue with regard to closing cleanly
        data.icon_path = fp.__enter__()
        atexit.register(fp.__exit__, None, None, None)

    data.license_radios = [
        sg.Radio(name, 1, default=False, key="license_" +
                 name, enable_events=True)
        for name in data.name_to_license
    ]
    return data


def main():

    sg.theme('Dark Blue 3')  # please make your creations colorful

    # initial = os.path.dirname(os.path.realpath(__file__))

    log = my_logger.get_logger()

    # https://en.wikipedia.org/wiki/List_of_Microsoft_Office_filename_extensions
    # Now we also support reading from Cricket Scorer Pro xml files so add xml
    extensions = (
        ("Excel or xml files", "*.x*"),
        ("ALL Files", "*.*"),

        ("All Excel files", "*.xl*"),
        ("Extensible Markup Language", "*.xml"),

        ("Excel workbook", "*.xlsx"),
        ("Excel macro-enabled workbook", "*.xlsm"),
        ("Legacy Excel worksheets", "*.xls"),
        ("Legacy Excel macro", "*.xlm"),

    )

    user_settings_file = sg.UserSettings()
    user_settings_file.get_filename
    # This seems to NEED to be called to initialise the default filename

    # Printing this in a Windows 8 virtualmachine at least breaks, with module __main__ has
    # no attribute __FILE__ - this works from a file not from a script
    # I think the problem is elsewhere
    # print("Using settings file:", user_settings_file.get_filename())
    # Must set this
    user_settings_file.set_location("cricket_scorer-cache.json")
    log.debug("Using settings file:", user_settings_file.get_filename())

    keys = {
        "spreadsheet_path": r"C:\Users\example\path\to\cricket.xlsx",
        "worksheet": "Sheet1",
        "total": "A2",
        "wickets": "B2",
        "overs": "C2",
        "innings": "D2",
        "logs_folder": "Please click \"Browse\" and specify a folder "
        "for logfiles to be put in!",
        # TODO: change this to live
        # "profile": "test_sender_args_excel",
        "profile": "excel_live",
        "log_level": "INFO",
        "logs_folder_toggle": True,
    }

    settings = dict.fromkeys(keys, "")
    saved_settings = {}

    if user_settings_file.exists():
        saved_settings.update(user_settings_file.read())
    else:
        log.debug(f"No settings file at {user_settings_file.get_filename()}")
        settings.update(keys)

    if set(saved_settings.keys()) != set(keys):
        try:
            if user_settings_file.exists():
                user_settings_file.delete_file()
        except Exception as e:
            log.error(
                f"Error deleting user settings file {user_settings_file.get_filename()}")
        saved_settings.clear()

    settings.update(saved_settings)

    sender_profiles = profiles.SENDER_PROFILES

    external_resources = get_resources()

    app_name = "cricket_scorer"
    # Append version, currently only in packaged version
    if hasattr(external_resources, "version"):
        app_name += " v" + str(external_resources.version)

    # yapf: disable
    licenses_layout = [
        [
            sg.Frame("Licenses for software components",
                     [
                         external_resources.license_radios,
                     ],
                     ),
        ],
        [
            sg.Frame("",
                     [
                         [
                             sg.Multiline(
                                 size=(120, 12),
                                 font=("arial", 13),
                                 key="license_multiline",
                                 autoscroll=False,
                                 echo_stdout_stderr=False,
                                 reroute_stdout=False,
                                 reroute_stderr=False,
                                 write_only=True,
                                 auto_refresh=True,
                                 disabled=True,
                             ),
                         ],
                     ],
                     ),
        ],
    ]
    # yapf: enable

    profile_names = sender_profiles.get_buildable_profile_names()
    profiles_listbox = [
        sg.Listbox(
            profile_names,
            default_values=[settings["profile"]],
            # [sender_profiles.get_buildable_profile_names()],
            size=(max(map(len, profile_names)), len(profile_names)),
            select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
            enable_events=True,
            key="profile",
        )
    ]

    user_settings_layout_excel_only_part = [
        [sg.Text("Worksheet name:", key="worksheet_name_text"),
         sg.Input(settings["worksheet"], key="worksheet")],
        [sg.Text("Cells where scores live in spreadsheet:",
                 key="cells_where_scores_text")],
        [
            sg.Text("Total:"),
            sg.Input(settings["total"], size=(9, 1), key="total"),
            sg.Text("Wickets:"),
            sg.Input(settings["wickets"], size=(9, 1), key="wickets"),
            sg.Text("Overs:"),
            sg.Input(settings["overs"], size=(9, 1), key="overs"),
            sg.Text("1st Innings:"),
            sg.Input(settings["innings"], size=(9, 1), key="innings"),
        ],
    ]

    user_settings_layout = [
        [
            sg.Text("Spreadsheet or xml:"),
            sg.FileBrowse(
                key="spreadsheet_selector",
                #  enable_events = True,
                target="spreadsheet_path",
                # initial_folder = "",
                # size=(30, 1),
                file_types=extensions),
            sg.Text(settings["spreadsheet_path"],
                    auto_size_text=True,
                    size=(80, 1),
                    key="spreadsheet_path")
        ],
        [sg.Frame("", user_settings_layout_excel_only_part,
                  key="user_settings_layout_excel_only_part")],
        [
            sg.Text("Logs folder:", pad=(5, 10)),
            sg.Checkbox(
                "", default=settings["logs_folder_toggle"], key="logs_folder_toggle"),
            sg.pin(
                sg.FolderBrowse(
                    key="logs_folder_selector",
                    target="logs_folder_selected",
                    # initial_folder=(
                    #     settings["logs_folder"]),
                ), ),
            # initial_folder = "",
            # size=(30, 1),
            sg.pin(
                sg.Text(settings["logs_folder"],
                        auto_size_text=True,
                        size=(80, 1),
                        key="logs_folder_selected"), ),
        ],
    ]

    user_actions_layout = [
        [
            sg.Button(
                "Run",
                font=("arial", 20),
                # Width is size of "Save & Quit" button text
                size=(10, 1),
                enable_events=True,
                pad=((5, 25), (5, 5)),
                key="run"),
            sg.Quit("Save & Quit", font=("arial", 20), pad=(
                (5, 25), (5, 5)), key="save_and_quit"),
            sg.Save(key="Save"),
            sg.Quit("Quit without saving settings", pad=(
                5, 5), key="quit_without_saving"),
            sg.VerticalSeparator(pad=((40, 40), (0, 0))),
            sg.Button(
                "Stop disconnect notifications",
                visible=True,
                font=("arial", 24),
                key="stop_disconnect_notifications",
                enable_events=True,
            ),
        ],
    ]

    status_text_format_warning_initial = {
        "font": ("arial", 24),
        # "relief": sg.RELIEF_SUNKEN,
        # "pad": (10, 10),
        "text_color": "black",
        "background_color": "red",
    }

    status_text_format_warning_initial_smaller = copy.deepcopy(
        status_text_format_warning_initial)
    status_text_format_warning_initial_smaller["font"] = ("arial", 16)

    status_layout = [
        [
            sg.Text(
                "|",
                key="spinning_char",
                font=("arial", 10),
                size=(1, 1),
                background_color="black",
            ),
            sg.Text(
                "Not running",
                key="is_running",
                # Padding here so row doesn't change height when other elements
                # are made visible. Could not find a better way to do this
                pad=(None, 20),
                size=(None, 1),
                **status_text_format_warning_initial),
            sg.Text("Not connected",
                    key="is_connected",
                    size=(None, 1),
                    **status_text_format_warning_initial),
            sg.pin(
                sg.Text("Settings changed, click Run to reload",
                        size=(16, 2),
                        auto_size_text=True,
                        **status_text_format_warning_initial_smaller,
                        key="settings_changed",
                        justification="center"), ),
            sg.pin(
                sg.Text(" " * 30,
                        key="status_error_message",
                        **status_text_format_warning_initial_smaller,
                        size=(30, 2))),
            sg.pin(
                sg.Text(
                    " " * 24,
                    key="general_error_message",
                    size=(24, 2),
                    **status_text_format_warning_initial_smaller,
                ), ),
        ],
    ]

    # In case need to import module level logger to initialise logging stuff
    my_logger.get_logger()
    log_level_names = list()
    for i in range(0, 1001):
        level_name = logging.getLevelName(i)
        if level_name != f"Level {i}":
            log_level_names.append(level_name)

    log_output_layout = [[
        sg.Text("Show log level and above:"),
        sg.OptionMenu(log_level_names,
                      size=(10, 2),
                      default_value=settings["log_level"],
                      key="log_level"),
        sg.Checkbox(
            "Autoscroll",
            default=True,
            enable_events=True,
            key="log_output_scroll_toggle",
        ),
    ],
        [
        sg.Multiline(
            size=(140, 15),
            font=("arial", 13),
            key="log_output",
            autoscroll=True,
            echo_stdout_stderr=False,
            reroute_stdout=False,
            reroute_stderr=False,
            write_only=True,
            auto_refresh=True,
            disabled=True,
        ),
    ]]

    config_tab_layout = [[sg.Frame("User settings", user_settings_layout, pad=(5, 15))],
                         [
                             sg.Frame(
                                 "",
                                 [
                                     [
                                         sg.Checkbox(
                                             "Toggle desktop notifications/taskbar "
                                             "popups when an error occurs",
                                             enable_events=True,
                                             default=True,
                                             key="desktop_error_notifications"),
                                     ],
                                 ],
                             ),
    ],
        [
                             sg.Frame(
                                 "",
                                 [
                                     [
                                         sg.Text(
                                             textwrap.dedent(f"""\
                             The scoreboard creates its own wifi network.
                             You will need to connect via wifi using these credentials:
                             SSID/network name: {RECEIVER_WIFI_SSID}
                             Password: {RECEIVER_WIFI_PASSWORD}
                             """)),
                                     ],
                                 ],
                             ),
    ]]

    dev_layout = [
        sg.Frame(
            "Developer/testing settings - only touch if you know what you're doing",
            [
                [sg.Text("Settings cache file:"),
                 sg.Text(user_settings_file.get_filename())],
                [sg.Button("Delete saved settings",
                           key="delete_saved_settings")],
                profiles_listbox,
            ],
            key="dev_layout",
            pad=(5, 15),
            font=("arial", 28),
        ),
    ]

    log_tab_layout = [
        [sg.Frame("Log output", log_output_layout, pad=(5, 15))],
    ]

    developer_tab_layout = [dev_layout]

    tab_group_layout = [
        [
            sg.Tab("Configuration", config_tab_layout, key="config_tab"),
            sg.Tab("Log output", log_tab_layout, key="log_tab"),
            sg.Tab("⛔", developer_tab_layout, key="developer_tab"),
            sg.Tab("About", licenses_layout, key="licenses_tab"),
        ],
    ]

    layout = [
        [sg.Frame("Status", status_layout,
                  key="status_row", pad=((5, 5), (0, 5)))],
        [
            sg.TabGroup(tab_group_layout,
                        font=("arial", 20),
                        key="tab_group_layout",
                        enable_events=True,
                        pad=((55, 5), (5, 5))),
        ],
        [
            sg.Frame(
                "User actions",
                user_actions_layout,
                vertical_alignment="center",
                pad=((5, 5), (10, 5)),
            )
        ],
    ]

    layout[-1].append(sg.Sizegrip())

    crash_window_text = ("Application exited in an unexpected way."
                         " If you exited it normally, please IGNORE this window and close it."
                         "\n"
                         "Otherwise consider getting this output (copy and paste "
                         "from the window below) to the developer."
                         "\n"
                         "Plus the most recent logfile(s), the folder is printed below."
                         "\n"
                         "Email: arghnews@hotmail.co.uk")

    crash_window_layout = [
        [
            sg.Multiline(
                crash_window_text,
                font=("arial", 16),
                size=(None, 4),
                auto_size_text=True,
                expand_x=True,
                write_only=True,
                auto_refresh=True,
                disabled=True,
                focus=True,
            ),
        ],
        [
            sg.Multiline(
                size=(140, 20),
                font=("arial", 12),
                key="crash_window_output",
                echo_stdout_stderr=True,
                #  reroute_stdout=True,
                #  reroute_stderr=True,
                write_only=True,
                auto_refresh=True,
                disabled=True,
                focus=True,
            ),
        ],
        [sg.Exit(font=("arial", 20))],
    ]

    state = types.SimpleNamespace(
        timer=BetterTimer(),
        settings=settings,
        saved_settings=saved_settings,
        running_settings={},
        scoredata=ScoreData(),
        running=False,
        done=False,
        do_run=False,
        connected=False,
        lost_connection_notifications=False,
        just_lost_connection=False,
        lost_connection_timer=make_countdown_timer(seconds=30, started=False),
        sender_connection=typing.Union[None, connection.Sender],
        consecutive_reader_errors=0,
        reader_timer=make_countdown_timer(seconds=3, started=False),
        logs_folder_toggle=settings["logs_folder_toggle"],
        spinning_char_timer=make_countdown_timer(seconds=2),
        spinning_char_index=0,
        general_error_flag=False,
        general_error_flag_timer=make_countdown_timer(
            seconds=15, started=False),
        desktop_error_notifications=True,
    )

    def _send_desktop_notification(title, message, log, app_name, app_icon, timeout=10):
        assert isinstance(app_icon, str)
        try:
            plyer.notification.notify(
                title=title,
                message=message,
                app_name=app_name,
                app_icon=app_icon,
                timeout=timeout,
            )
        except Exception as e:
            log.debug(f"Error sending desktop notification {e}, {title}")

    send_desktop_notification = functools.partial(_send_desktop_notification,
                                                  log=log,
                                                  app_name=app_name,
                                                  app_icon=str(external_resources.icon_path))

    args = None

    try:
        window = sg.Window(
            app_name,
            layout,
            icon=external_resources.icon_path,
            finalize=True,
            return_keyboard_events=True,
            resizable=True,
            font=("arial", 13),
            enable_close_attempted_event=True,
        )
        window.set_min_size((640, 480))
        window["status_row"].expand(expand_x=True, expand_row=True)

        log_output_filter = MyLogFilter()
        add_log_gui_handler(log_output_filter, window, "log_output", log, state,
                            send_desktop_notification)

        args = gui_main_loop(log, sender_profiles, window, state, user_settings_file,
                             log_output_filter, send_desktop_notification,
                             external_resources.name_to_license)

        stop_running(state)

    except Exception as e:
        # If an unexpected exception occurs, display a crash window with a
        # stacktrace and additional information here
        trace = traceback.format_exc()
        log.error(f"Uncaught exception {e}: {trace}")
        window2 = sg.Window("Crash print window",
                            layout=crash_window_layout,
                            force_toplevel=True,
                            finalize=True)
        s = f"""
            {platform.platform()}
            {platform.python_build()}
            {platform.uname()}
        """
        s += "\n"
        if (state.running and state.running_settings is not None
                and "logs_folder" in state.running_settings
                and "logs_folder_toggle" in state.running_settings
                and state.running_settings["logs_folder_toggle"]
                and state.running_settings["logs_folder"]):

            logfile_path = state.running_settings["logs_folder"]
            s += f"Logs folder: {logfile_path}\n"
        else:
            s += "No logfile\n"
        window2["crash_window_output"].print(f"System info: {s}")
        window2["crash_window_output"].print(f"Exception: {trace}")
        window2.bring_to_front()
        window2.force_focus()
        while True:
            # Ensure this has a timeout otherwise stuff doesn't work on windows:
            # https://github.com/PySimpleGUI/PySimpleGUI/issues/1077
            win, event, _ = sg.read_all_windows(10)
            if event in ("save_and_quit", sg.WIN_CLOSED, "quit_without_saving"):
                window.close()
            if win == window2 and event in (sg.WIN_CLOSED, "Exit"):
                break

    finally:
        if "window2" in locals() and window2 is not None:
            window2.close()
        log.debug("Timing summary:\n" + "\n".join(state.timer.summary()))
        if args is not None:
            args.close()
        log.debug("Done, closing")
        window.close()


# def get_ssids():
#     import re
#     import subprocess
#     cmd = "netsh wlan show interfaces".split()
#     try:
#         output = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
#     except subprocess.TimeoutExpired:
#         return []

#     if output.returncode != 0:
#         return []

#     text, lines = output.stdout, output.stdout.splitlines()
#     if not re.search(r"There are \d+ interfaces on the system:", text):
#         return []

#     ssid_groups = [re.search(r"(?:^|\s+)SSID\s+: (.*)$", line) for line in lines]
#     return [m.group(1) for m in ssid_groups if m]


def setup_args(log, sender_profiles, state):
    args, worked = setup_args_impl(log, sender_profiles, state)
    if not worked:
        if args is not None:
            args.close()
        return None
    return args


def setup_args_impl(log, sender_profiles, state):
    # This may or may not, depending on the profile, attach a file handler to the logger
    # It's possible this may fail, but we should continue anyway

    def log_error(message):
        log.debug(
            f"Error occurred, see ERROR message after this, stacktrace:\n{traceback.format_exc()}")
        log.error(message)

    state.timer.start("init profile build")
    try:
        logs_folder = state.settings["logs_folder"]
        logs_folder = logs_folder if state.settings["logs_folder_toggle"] else None
        profile_name = state.settings["profile"]

        log.info(f"Building profile {profile_name} args")
        log.debug(f"Logs folder argument set to {logs_folder}")
        args = sender_profiles.build_profile(profile_name,
                                             logs_folder=logs_folder,
                                             overwrite_if_none=True)
    except Exception as e:
        log_error(f"Unable to initialise args profile: {e}")
        return None, False
    finally:
        state.timer.stop("init profile build")

    state.timer.start("init logger")
    try:
        log.info("Setting up additional logging if selected")
        args.init_logger()
    except Exception as e:
        log_error("Unable to initialise logger (probably check the logs folder in the "
                  f"Configuration tab): {e}")
        return args, False
    finally:
        state.timer.stop("init logger")

    state.timer.start("init socket")
    try:
        log.info("Setting up socket and score reader")
        args.init_all()
    except Exception as e:
        log_error(
            f"Error during initialisation (probably of the network socket): {e}")
        return args, False
    finally:
        state.timer.stop("init socket")

    state.timer.start("init sender connection")
    try:
        log.info("Initialising sender connection")
        state.sender_connection = connection.Sender(args)
    except Exception as e:
        log_error(f"Error from sender_connection setup: {e}")
        return args, False
    finally:
        state.timer.stop("init sender connection")

    state.timer.start("init score reader")
    try:
        log.info("Refreshing score reader with latest settings")

        # TODO: this is a bodge for now because I think doing it "properly" will
        # end up doing a bigger architectural rework anyway

        if hasattr(args.score_reader, "refresh_excel"):
            args.score_reader.refresh_excel(state.settings["spreadsheet_path"],
                                            state.settings["worksheet"], state.settings["total"],
                                            state.settings["wickets"], state.settings["overs"],
                                            state.settings["innings"])
        elif hasattr(args.score_reader, "refresh_xml"):
            args.score_reader.refresh_xml(state.settings["spreadsheet_path"])

    except Exception as e:
        log_error(
            f"Error refreshing score reader (opening/reading from Excel): {e}")
        return args, False
    else:
        state.running_settings = copy.deepcopy(state.settings)
        state.running = True
    finally:
        state.timer.stop("init score reader")

    return args, True


def add_log_gui_handler(log_output_filter, window, key, logger, state, send_desktop_notification):
    p = functools.partial(print_to_output,
                          window=window,
                          key=key,
                          state=state,
                          send_desktop_notification=send_desktop_notification)
    h = MyLogHandler(p)
    h.setFormatter(my_logger.get_formatter())
    h.addFilter(log_output_filter)
    logger.addHandler(h)


class MyLogHandler(logging.StreamHandler):
    def __init__(self, log_func) -> None:
        super().__init__(stream=io.StringIO())
        self._log_func = log_func

    def emit(self, record: logging.LogRecord):
        self._log_func(self, record)


def print_to_output(handler, record: logging.LogRecord, window, key, state,
                    send_desktop_notification):
    background_color = None
    # text_color = "black"
    if record.levelno > logging.INFO:
        # background_color = "red",
        background_color = "#FF696C"  # A less intense red that's more legible
    if record.levelno >= logging.ERROR:
        if not state.general_error_flag and state.desktop_error_notifications:
            send_desktop_notification("cricket_scorer error",
                                      "An error has occurred, check the logs tab")
        state.general_error_flag = True
        state.general_error_flag_timer.reset()
        window["general_error_message"].update("Error (check the logs tab for more info)",
                                               visible=True)
    window[key].update(value=handler.formatter.format(record) + "\n",
                       background_color_for_value=background_color,
                       append=True)


def save_settings(log, user_settings_file, state):
    s = "\n" + "\n".join(f"{k}: {v}" for k, v in state.settings.items())
    log.debug(f"Saving settings to {user_settings_file.get_filename()}", s)

    user_settings_file.write_new_dictionary(state.settings)
    state.saved_settings = copy.deepcopy(state.settings)


def handle_events(log, user_settings_file, state, event, window, values, name_to_license: dict):
    """Returns looping, done"""
    if event == "Save":
        save_settings(log, user_settings_file, state)

    elif event.startswith("license_"):
        license_name = event[len("license_"):]
        log.debug(f"Event, showing license: {event}")
        window["license_multiline"].update(name_to_license[license_name])

    elif event == "save_and_quit" or event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT:
        log.info("Saving and quitting")
        save_settings(log, user_settings_file, state)
        state.done = True

    elif event == "quit_without_saving":
        log.info("Quitting without saving")
        state.done = True

    elif event == "delete_saved_settings":
        log.info("Deleting saved settings")
        user_settings_file.delete_file()
        state.saved_settings.clear()

    elif event == "log_output_scroll_toggle":
        # TODO: consider moving this to the main loop bit, so we don't have to touch
        # the window in here
        window["log_output"].update(
            autoscroll=values["log_output_scroll_toggle"])

    elif event == "run":
        # if not state.running or settings_changed(state.settings,
        #                                          state.running_settings):
        state.do_run = True
        log.info("Run event received, will run program next time round")

    elif event == "stop_disconnect_notifications":
        log.debug("Disconnect notifications ceased")
        state.lost_connection_notifications = False

    elif event in ("__TIMEOUT__"):
        pass

    else:
        # So many possible unhandled events from every keyboard input etc.
        # Don't log, just ignore
        pass


def update_settings(settings, values, log_output_filter):
    """Update the settings dict based on the window.read()'s values dict"""

    for k, v in values.items():
        if k == "spreadsheet_selector":
            if v:
                settings["spreadsheet_path"] = v
        elif k == "logs_folder_toggle":
            settings["logs_folder_toggle"] = v
            pass
        elif k == "logs_folder_selector":
            if v:
                settings["logs_folder"] = v
        elif k == "profile":
            if v:
                assert isinstance(v, list)
                assert len(v) == 1
                cp = settings["profile"]
                settings["profile"] = v[0]
                if settings["profile"] != cp:
                    print("Updating settings[profile] to", settings["profile"])
        elif k == "log_level":
            log_output_filter.setLevel(v)
            settings["log_level"] = v
        # In PySimpleGUI 4.45.0 at least, the sg.pin values don't occur here
        # So we'll remove this assuming this holds
        # elif k == 0 or k == 1:
        #     # To allow past the sg.pin elements which can't have keys set
        #     pass
        elif k in ("worksheet", "total", "wickets", "overs", "innings"):
            settings[k] = v
        elif k in ("log_output_scroll_toggle", "tab_group_layout", "desktop_error_notifications"):
            pass
        elif k.startswith("license_"):
            pass
        else:
            assert False, (
                f"Unhandled value in gui values \"{k}\": \"{v}\", " f"values: {values}")


def stop_running(state):
    state.running_settings = {}
    state.running = False
    state.connected = False
    state.lost_connection_notifications = False
    state.just_lost_connection = False
    state.sender_connection = None
    state.consecutive_reader_errors = 0
    state.reader_timer.reset()
    # if args is not None:
    #     args.close()


def settings_changed(settings: dict, running_settings: dict) -> bool:
    differing_keys = {
        "spreadsheet_path", "worksheet", "total", "wickets", "overs", "innings", "profile",
        "logs_folder_toggle"
    }

    if any(settings[k] != running_settings[k] for k in differing_keys):
        return True

    assert running_settings["logs_folder_toggle"] == settings["logs_folder_toggle"]
    if running_settings[
            "logs_folder_toggle"] and running_settings["logs_folder"] != settings["logs_folder"]:
        return True

    return False


def gui_main_loop(log: my_logger.LogWrapper, sender_profiles, window: sg.Window,
                  state: types.SimpleNamespace, user_settings_file, log_output_filter,
                  send_desktop_notification, name_to_license: dict):
    args: Args = None

    # printer = OnlyPrintOnDiff()
    # _print = lambda *args, **kwargs: printer.print(*args, **kwargs)
    # _print = lambda *args, **kwargs: None

    status_text_format_ok = {"background_color": "green"}
    status_text_format_warning = {"background_color": "red"}
    old_scoredata = state.scoredata

    log.debug("Starting main gui loop")
    window["general_error_message"].update(visible=False)

    # Set True during development to show the warnings in the status bar
    test_show = False
    if test_show:
        window["general_error_message"].update(visible=True)

    state.timer.start("loop")
    while not state.done:
        event, values = window.read(10)

        old_spreadsheet_path = state.settings.get("spreadsheet_path")

        state.timer.start("handle events")
        handle_events(log, user_settings_file, state, event,
                      window, values, name_to_license)
        state.timer.stop("handle events")

        if state.done:
            log.debug("state.done is True, breaking from main loop")
            break

        # Not sure on order of update_settings and handle_events
        # Update the state.settings dict
        update_settings(state.settings, values, log_output_filter)

        # Bodge-ish fix for now, for live. Need to change profile between
        # excel_live and xml_live depending on selected filetype extension
        spreadsheet_path = state.settings.get("spreadsheet_path")
        if spreadsheet_path != old_spreadsheet_path:
            # TODO: add something in to allow settings a test mode so don't go
            # insane when selecting files to test and this overwrites it. For
            # live this is fine as only xml_live or excel_live should ever be
            # selected
            # Also this breaks on Ubuntu as the excel_live profile is only
            # loaded on Windows (as you won't be able to open Excel on Linux).
            # Again this only matters for testing.

            i = 0
            profiles = window["profile"].get_list_values()
            if spreadsheet_path.lower().endswith(".xml"):
                log.debug(f"spreadsheet_path from {old_spreadsheet_path} "
                          f"to {spreadsheet_path}, using xml_live profile")
                state.settings["profile"] = "xml_live"
                i = profiles.index("xml_live")
            else:
                log.debug(f"spreadsheet_path from {old_spreadsheet_path} "
                          f"to {spreadsheet_path}, using excel_live profile")
                state.settings["profile"] = "excel_live"
                i = profiles.index("excel_live")

            # Must set the window ListBox here as it's the source of truth for the profile
            window["profile"].update(set_to_index=i)

        # Set a bool toggling whether desktop error notifications are enabled
        state.desktop_error_notifications = values["desktop_error_notifications"]

        # Toggle logs folder gui input elements based on the toggle
        window["logs_folder_selected"].update(
            visible=state.settings["logs_folder_toggle"])
        window["logs_folder_selector"].update(
            visible=state.settings["logs_folder_toggle"])

        # https://github.com/PySimpleGUI/PySimpleGUI/issues/1964
        # Make it so that the FolderBrowse initial folder is set correctly
        # This is a class level variable, so be careful if add in another folder selector
        window["logs_folder_selector"].InitialFolder = state.settings["logs_folder"]
        window["spreadsheet_selector"].InitialFolder = \
            os.path.dirname(state.settings["spreadsheet_path"])

        state.timer.start("running")
        if state.do_run:
            log.info("Program restarting backend")
            stop_running(state)
            if args is not None:
                args.close()
            print(state.settings.get("profile"))
            xi = 0
            args = setup_args(log, sender_profiles, state)
            log.info("Trying to run program")
            state.do_run = False
            window["log_tab"].select()
            # state.running will have been set True or False by setup_args
            # depending on whether it was successful
            if state.running:
                log.info("Successfully running")
            else:
                log.info("Failed to run program (see log)")
        state.timer.stop("running")

        if state.settings.get("spreadsheet_path").endswith("xml"):
            # Only want to show things like cell selection if user has selected
            # an excel spreadsheet, if using xml then don't show it
            window["user_settings_layout_excel_only_part"].update(
                visible=False)
        else:
            window["user_settings_layout_excel_only_part"].update(visible=True)

        # If running, read the score from Excel
        state.timer.start("reader")
        if state.running and state.reader_timer.just_expired():
            state.reader_timer.reset()
            assert args is not None, "If state.running, args should not be None"
            try:
                state.scoredata = args.score_reader.read_score()
            except Exception as e:
                log.error(f"Error reading score from Excel spreadsheet: {e}. "
                          "(Once fixed click \"Run\" to restart the program)")
                state.consecutive_reader_errors += 1
                # TODO: add notification if this happen a lot, probably means
                # excel has closed or something like that
            else:
                state.consecutive_reader_errors = 0

            # Log if the score has changed
            if old_scoredata != state.scoredata:
                score_str, err = state.scoredata.score_as_str(), state.scoredata.error_msg
                old_score_str = old_scoredata.score_as_str()
                err_msg = f", error: {err}" if err else ""
                log.info(f"Score read from Excel changed to: {score_str}{err_msg}, "
                         f"was {old_score_str}")
                old_scoredata = state.scoredata
        state.timer.stop("reader")

        # Show/hide error message about consecutive score reads failing. A
        # common possible cause is if Excel has been closed
        if state.consecutive_reader_errors > 10 or test_show:
            window["status_error_message"].update(
                "Multiple attempts to read score values from Microsoft Excel have failed",
                visible=True,
                **status_text_format_warning)
        else:
            window["status_error_message"].update(visible=False)

        # Update the connection with the latest score data, and service the network
        state.timer.start("network poll")
        if state.running:
            state.sender_connection.poll(state.scoredata.score)
        state.timer.stop("network poll")

        just_lost_connection = False
        if state.running and state.sender_connection.is_connected():
            if not state.connected:
                log.info("Connected!")
            state.connected = True
            window["is_connected"].update(
                "Connected    ", **status_text_format_ok)
        else:
            window["is_connected"].update(
                "Not connected", **status_text_format_warning)
            if state.connected:
                just_lost_connection = True
                state.connected = False
            if just_lost_connection and not state.lost_connection_notifications:
                state.lost_connection_notifications = True
                state.lost_connection_timer.reset()

        state.timer.start("desktop notify disconnect")
        send_notify = False
        if just_lost_connection:
            log.info("Disconnected!")
            send_notify = True
        elif state.lost_connection_notifications and state.lost_connection_timer.just_expired():
            log.debug("Lost connection notification timeout")
            state.lost_connection_timer.reset()
            send_notify = True

        if send_notify:
            log.debug("Sending desktop notification about lost connection")
            send_desktop_notification("cricket_scorer lost_connection",
                                      "cricket_scorer has lost connection")
        window["stop_disconnect_notifications"].update(
            visible=state.lost_connection_notifications)
        state.timer.stop("desktop notify disconnect")

        if state.running:
            window["is_running"].update("Running    ", **status_text_format_ok)
        else:
            window["is_running"].update(
                "Not running", **status_text_format_warning)

        if test_show or state.running and settings_changed(state.settings, state.running_settings):
            window["settings_changed"].update(visible=True)
        else:
            window["settings_changed"].update(visible=False)

        # Spinner to show we haven't frozen
        spinning_chars = ["|", "/", "-", "\\"]
        if state.spinning_char_timer.just_expired():
            state.spinning_char_timer.reset()
            state.spinning_char_index += 1
            state.spinning_char_index %= len(spinning_chars)
            window["spinning_char"].update(
                spinning_chars[state.spinning_char_index])

        if state.general_error_flag_timer.just_expired():
            state.general_error_flag = False
            state.general_error_flag_timer.reset()
            if not test_show:
                window["general_error_message"].update(visible=False)

        # printer.print_contents_if_diff()

    log.info("Exiting main loop, program should terminate in a moment")

    state.timer.stop("loop")
    state.running_settings.clear()
    # printer.print_contents_if_diff()
    return args


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
