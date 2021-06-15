#!/usr/bin/env python3

import copy
import io
import multiprocessing
import os
import sys
import time
import types
import typing

import PySimpleGUI as sg
import plyer

from cricket_scorer.misc import profiles
from cricket_scorer.net import connection
from cricket_scorer.score_handlers.scoredata import ScoreData

# This will be either reading from the excel spreadsheet via xlwings
# Or from the I2C ports
# Or just prints out numbers as a dummy generator
def score_reader_f(*args):
    print("score_reader_f sender started with args:", *args)
    for num in range(1000000):
        # print("Getting net num", num)
        epoch_time = int(time.time()) // 5
        yield bytes([epoch_time % 10] * 9)

# This will be the networking code function that control will be handed to that
# will send it to the other scoreboard
async def score_sender_func(*args):
    print("score_sender_func started with args:", *args)
    while 1:
        #  print("score sender start iter")
        val = (yield)
        #  print("Sending", val, "to scoreboard")

class OnlyPrintOnDiff:
    def __init__(self):
        self.buf = io.StringIO()
        self.prev = None
    def print(self, *args, **kwargs):
        print(*args, file = self.buf, **kwargs)
    def print_contents_if_diff(self):
        contents = self.buf.getvalue()

        if contents != self.prev:
            print(contents, end = "")

        self.prev = contents
        self.buf = io.StringIO()

class BetterTimer:
    def __init__(self) -> None:
        self._timers = {}
    def restart(self):
        self._timers.clear()
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
        for name, (t, _) in self._timers.items():
            print(name, "->", t)

def notify_disconnected(title, message, timeout = 15):

    plyer.notification.notify(
    title = title,
    message = message,
    timeout = timeout,
    )

def main():

    sg.theme('Dark Blue 3')  # please make your creations colorful

    initial = os.path.dirname(os.path.realpath(__file__))

    # https://en.wikipedia.org/wiki/List_of_Microsoft_Office_filename_extensions
    extensions = (
        ("All Excel files", "*.xl*"),
        ("ALL Files", "*.*"),
        ("Excel workbook", "*.xlsx"),
        ("Excel macro-enabled workbook", "*.xlsm"),
        ("Legacy Excel worksheets", "*.xls"),
        ("Legacy Excel macro", "*.xlm"),
        )

    user_settings_file = sg.UserSettings()
    # This seems to NEED to be called to initialise the default filename

    # Printing this in a Windows 8 virtualmachine at least breaks, with module __main__ has
    # no attribute __FILE__ - this works from a file not from a script
    # I think the problem is elsewhere
    # print("Using settings file:", user_settings_file.get_filename())
    # Must set this
    user_settings_file.set_location("cricket-scorer-cache.json")
    print("Using settings file:", user_settings_file.get_filename())

    keys = {
            "spreadsheet_path": r"C:\Users\example\path\to\cricket.xlsx",
            "worksheet": "Sheet1",
            "total": "A2",
            "wickets": "B2",
            "overs": "C2",
            "innings": "D2",
            "logs_folder": "",
            # TODO: change this to live
            "profile": "test_sender_args_excel",
    }

    settings = dict.fromkeys(keys, "")
    saved_settings = {}

    if user_settings_file.exists():
        saved_settings.update(user_settings_file.read())
    else:
        print(f"No settings file at {user_settings_file.get_filename()}")
        settings.update(keys)

    if set(saved_settings.keys()) != set(keys):
        try:
            user_settings_file.delete_file()
        except Exception as e:
            print(f"Error deleting user settings file {user_settings_file.get_filename()}",
                  file=sys.stderr)
        saved_settings.clear()

    settings.update(saved_settings)

    sender_profiles = profiles.sender_profiles

    profile_names = sender_profiles.get_buildable_profile_names()
    profiles_listbox = [sg.Listbox(
        profile_names,
        default_values=[settings["profile"]],
        # [sender_profiles.get_buildable_profile_names()],
        size=(max(map(len, profile_names)), len(profile_names)),
        select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,
        enable_events=True,
        key="profile",
    )]

    # settings = {
    #         "spreadsheet_path": r"",
    #         #  "spreadsheet_selector": r"C:\Users\justin\cricket.xlsx",
    #         "worksheet": "Sheet1",
    #         "total": "A2",
    #         "wickets": "B2",
    #         "overs": "C2",
    #         "innings": "D2",
    #         "logs_folder": "",
    #         # "serialisation_order": ["total", "wickets", "overs", "innings"],
    #         }
    layout1 = [
                #  [sg.Text('Spreadsheet')
                    #  ],

                #  [sg.FileBrowse(key = "spreadsheet_selector",
                    #  enable_events = True,
                    #  initial_folder = initial, file_types = extensions)
                    #  ],

                [sg.Text("Spreadsheet:"),
                    sg.FileBrowse(key = "spreadsheet_selector",
                        #  enable_events = True,
                        target = "spreadsheet_path",
                        initial_folder=os.path.dirname(settings["spreadsheet_path"]),
                        # initial_folder = "",
                        # size=(30, 1),
                        file_types=extensions),
                    sg.Text(settings["spreadsheet_path"], auto_size_text = True,
                        size = (120, 1),
                        key = "spreadsheet_path")
                    ],

                # [sg.Text("Workbook name:"), sg.Input(settings["worksheet"],
                [sg.Text("Worksheet name:"), sg.Input(settings["worksheet"],
                    key = "worksheet")
                    ],

                [sg.Text("Cell where scores live in spreadsheet:")
                    ],
                [
                    sg.Text("Total:"), sg.Input(settings["total"],
                        size = (9, 1), key = "total"),
                    sg.Text("Wickets:"), sg.Input(settings["wickets"],
                        size = (9, 1), key = "wickets"),
                    sg.Text("Overs:"), sg.Input(settings["overs"],
                        size = (9, 1), key = "overs"),
                    sg.Text("1st Innings:"), sg.Input(settings["innings"],
                        size = (9, 1), key = "innings"),
                    ],

                [sg.Text("Logs folder:"),
                    sg.FolderBrowse(key = "logs_folder_selector",
                        #  enable_events = True,
                        target = "logs_folder_selected",
                        initial_folder=(settings["logs_folder"]),
                    ),
                        # initial_folder = "",
                        # size=(30, 1),
                    sg.Text(settings["logs_folder"], auto_size_text = True,
                        size = (120, 1),
                        key = "logs_folder_selected")
                    ],

            [sg.Button("Delete saved settings", key = "delete_saved_settings")],
            [sg.Text("Settings cache file:"),
                sg.Text(user_settings_file.get_filename())],

                # [sg.Checkbox("Enable error cell",
                #     default = settings["enable_error_cell"],
                #     key = "enable_error_cell"),
                #     #  sg.Text("Error cell:", key = "error_cell_label"),
                #     sg.Input(settings["error_cell"], size = (7, 1),
                #         key = "error_cell",
                #         visible = settings["enable_error_cell"]),
                #     ],

                profiles_listbox,
                [sg.Button("Run", enable_events = True, key = "run"),
                    sg.Text(size = (50, 1), auto_size_text = True,
                        key = "run_label")],
                [sg.Save(key="Save")],
                #  [sg.Button("Run/Reload", key = "reload")],
                [sg.Quit("Save & Quit", pad = (5, 30), key="save_and_quit")],
                [sg.Quit("Quit without saving settings", pad=(
                    5, 30), key="quit_without_saving")],
              ]

    layout2 = [
        [sg.Text("hi"), sg.Text("there")],
        # sg.Sizegrip(),
    ]

    status_text_format_warning_initial = {
        "font": ("arial", 24),
        "relief": sg.RELIEF_SUNKEN,
        "pad": (10, 10),
        "text_color": "black",
        "background_color": "red",
    }

    layout3 = [
            [
                sg.Text("Not running", key="is_running",
                        **status_text_format_warning_initial),
                sg.Text("Not connected", key="is_connected",
                        **status_text_format_warning_initial),
                sg.Text("Settings have changed, click \"Save\"to save",
                        key="settings_changed")
            ],
    ]

    layout = [
        [sg.Frame("Status", layout3)],
        [sg.Frame("My frame here", layout1)],
        [sg.Frame("Frame 2", layout2)],
        [sg.Sizegrip()],
    ]

    # layout[-1].append(sg.Sizegrip())

    #  layout = [[sg.FileBrowse(initial_folder = initial, file_types = extensions)]]

    # layout =  [[sg.Button('Ok'), sg.Button('Cancel')]]

    # layout =  [[sg.FileBrowse()]]

    window = sg.Window('Cricket Scorer - Spreadsheet selector', layout,
            finalize = True,
            # size = (800, 600),
            return_keyboard_events = True,
            resizable=True,
            )
    window.set_min_size((640, 480))

    # args = sender_profiles.build_profile(settings["profile"])

    # print("Arguments from profile used:", args)

    # sender_connection = connection.Sender(args)

    # printer = OnlyPrintOnDiff()
    # _print = lambda *args, **kwargs: printer.print(*args, **kwargs)
    # _print = lambda *args, **kwargs: None

    # /home/justin/py/plyer_test/notify.py

    # timer = BetterTimer()
    # started = 0
    scoredata = ScoreData()
    # connected = False
    # running = False
    # running_settings: typing.Union[None, dict] = None

    # still_going = True
    # my_settings = {}
    # ret = "CONTINUE"
    # while ret == "CONTINUE":

    state = types.SimpleNamespace(timer=BetterTimer(), started=0, running=False,
                            connected=False)

    while True:
        with sender_profiles.build_profile(settings["profile"]) as args:
            print("Arguments from profile used:", args)
            sender_connection = connection.Sender(args)
            if loop(window, args, sender_connection, state,
                settings, saved_settings, user_settings_file,
                scoredata):
                break

    state.timer.summary()

    window.close()

# TODO: yes
def loop(window, args, sender_connection, state,
         settings, saved_settings, user_settings_file,
         scoredata):

    done = False
    status_text_format_ok = {"background_color": "green"}
    status_text_format_warning = {"background_color": "red"}

    printer = OnlyPrintOnDiff()
    _print = lambda *args, **kwargs: printer.print(*args, **kwargs)

    state.timer.start("loop")
    while True:
        _print()
        if state.started == 1:
            print("Restarting timer")
            state.timer.restart()
            state.started = 2

        if state.running:
            window["is_running"].update(**status_text_format_ok)
        else:
            window["is_running"].update(**status_text_format_warning)
        if state.connected:
            window["is_connected"].update(**status_text_format_ok)
        else:
            window["is_connected"].update(**status_text_format_warning)

        state.timer.start("window.read")
        event, values = window.read(timeout = 10)
        state.timer.stop("window.read")
        # if values["spreadsheet_selector"]:
        #     values["spreadsheet"] = values["spreadsheet_selector"]
        #     settings["spreadsheet"] = values["spreadsheet_selector"]

        _print(event)

        if event == "Save":
            #  user_settings_file["spreadsheet"] = spreadsheet
            #  settings.pop("spreadsheet_selector", None)
            # for k, v in values.items():
            # for k, v in [(k, values[k]) for k in settings.keys()]:
            # for k in settings.keys():
            #     if k not in values:
            #         continue
            #     v = values[k]
            #     if isinstance(v, str) and v:
            #         settings[k] = v
            #     else:
            #         settings[k] = v
            _print("Saving settings", settings)

            s = set(values.keys()) & set(settings.keys())
            _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])

            user_settings_file.write_new_dictionary(settings)
            saved_settings = copy.deepcopy(settings)

        if event == "save_and_quit" or event == sg.WIN_CLOSED:
            print(args.score_reader)
            print(type(args.score_reader))
            user_settings_file.write_new_dictionary(settings)
            done = True
            break

        if event == "quit_without_saving":
            done = True
            break

        if event == "run":
            _print("Run")
            _print(settings)
            _print(values)
            s = set(values.keys()) & set(settings.keys())
            _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])

            _print("Calling reader.start with " + str(settings))

            # if running_settings is not None \
            #         and settings["profile"] != running_settings["profile"]:

            #     # Feels messy
            #     sender_connection = None
            #     args = None

            #     args = sender_profiles.build_profile(settings["profile"])
            #     sender_connection = connection.Sender(args)

            state.running = True

            args.score_reader.refresh_excel(settings["spreadsheet_path"],
                            settings["worksheet"], settings["total"],
                            settings["wickets"], settings["overs"],
                            settings["innings"])
            # args.score_reader.refresh_excel(*list(settings.values()))
            state.started = 1
            # running_settings = copy.deepcopy(settings)

            # Convert Args to typing.ContextManager?
            # can simplify init stuff?
            # have this be a function, parameters including args and sender_connection
            # can make sure to close them cleanly
            # context managers more?
            # Need to properly consider, and handle closing of stuff now

        if event == "delete_saved_settings":
            user_settings_file.delete_file()
            saved_settings.clear()
            print("Deleting cached file")
            pass

        _print("Event, values:", event, values)
        _print(window["spreadsheet_path"])

        for k, v in values.items():
            if k == "spreadsheet_selector":
                if v:
                    settings["spreadsheet_path"] = v
            elif k == "logs_folder_selector":
                if v:
                    settings["logs_folder"] = v
            elif k == "profile":
                if v:
                    assert isinstance(v, list)
                    assert len(v) == 1
                    settings["profile"] = v[0]
            elif k in settings:
                settings[k] = v
            else:
                assert False, f"Unhandled value in gui values \"{k}\": \"{v}\""

        state.timer.start("reader")
        if state.started > 0:
            old_scoredata = scoredata
            scoredata = args.score_reader.read_score()
            if old_scoredata != scoredata:
                _print("New scoredata:", scoredata)
        state.timer.stop("reader")

        state.timer.start("network poll")
        if state.started > 0:
            sender_connection.poll(scoredata.score)
        state.timer.stop("network poll")

        if sender_connection.is_connected():
            state.connected = True
            window["is_connected"].update("Connected")
        else:
            window["is_connected"].update("Not connected")
            if state.connected:
                state.connected = False
                state.timer.start("desktop notify disconnect")
                notify_disconnected("cricket-scorer disconnected",
                                    "cricket-scorer has lost connection")
                state.timer.stop("desktop notify disconnect")

        if state.running:
            window["is_running"].update("Running")
        else:
            window["is_running"].update("Not running")

        if settings != saved_settings:
            window["run_label"].update("Config changed. Click \"Run\" to reload, "
                                        "click \"Save\" to save", visible=True)
        else:
            window["run_label"].update(visible=False)

        # Update gui
        # if values["spreadsheet_selector"]:
        # window["spreadsheet_text"].update(values["spreadsheet_selector"])
        # settings["spreadsheet"] = values["spreadsheet_selector"]

        #  _print(settings)
        #  _print(values)
        s = set(values.keys()) & set(settings.keys())
        _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])
        _print("Settings:", settings)
        _print("Saved settings:", saved_settings)
        _print("Values:", values)
        # if saved_settings != settings:
        # if any(True for k in s if values[k] != settings[k]):
        #  if values != settings:
        _print("Updating")

        # else:
            # _print("Not showing")
            # window["run_label"].update(visible = False)

        #  if values == last_values:
            #  continue

            #  #  _print("Updating!")
            #  #  _print("spreadsheet now:", spreadsheet)
        #  if values["sheet"]:
            #  settings["sheet"] = values["sheet"]
            #  #  _print("spreadsheet now:", spreadsheet)
            #  window["sheet"].update(settings["sheet"])

        printer.print_contents_if_diff()
        #  printer = OnlyPrintOnDiff(printer)
    #  print("Selected file at", values["Browse"])

    state.timer.stop("loop")
    return done

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
