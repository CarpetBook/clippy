import PySimpleGUI as sg
import ffmpeg
from subprocess import CREATE_NO_WINDOW

import os
import humanize

from helpers import timecalc as tc
from helpers import ffmpeg_processor as fp
from helpers import icon

sg.theme("BrightColors")  # Add too much color

RES_OPTIONS = [
    "2160p (4K)",
    "1440p (2K)",
    "1080p",
    "720p",
    "480p",
    "360p",
    "240p",
    "144p",
]

FFMPEG_LOC = "bin/ffmpeg"
FFPROBE_LOC = "bin/ffprobe"
SCISSORS_ICON = icon.SCISSORS_ICON

DISCORD_LIMIT = 25 * 1024 * 1024

# All the stuff inside your window.
layout = [
    [
        sg.Text("File to be clipped"),
        sg.Push(),
        sg.InputText(key="input_file", disabled=True, enable_events=True),
        sg.FileBrowse("Browse"),
    ],
    [
        sg.Text("Output"),
        sg.Push(),
        sg.InputText(key="output_file"),
        sg.FileSaveAs(file_types=(("MP4", "*.mp4"),)),
    ],
    [
        sg.Text("Start time:", key="start_time_label"),
        sg.InputText(
            "00:00:00", size=(10, 1), key="start_time_input", enable_events=True
        ),
        sg.Push(),
        sg.Text("End time:", key="end_time_label"),
        sg.InputText(
            "99:99:99", size=(10, 1), key="end_time_input", enable_events=True
        ),
    ],
    [
        sg.Slider(
            range=(0, 100),
            resolution=0.001,
            default_value=0,
            orientation="h",
            expand_x=True,
            disable_number_display=True,
            key="start_time_slider",
            enable_events=True,
        ),
        sg.Slider(
            range=(0, 100),
            resolution=0.001,
            default_value=100,
            orientation="h",
            expand_x=True,
            disable_number_display=True,
            key="end_time_slider",
            enable_events=True,
        ),
    ],
    [sg.Text("", key="clip_length", text_color="red")],
    [
        sg.Frame(
            "Export settings",
            layout=[
                [
                    sg.Text("Resolution"),
                    sg.Combo(
                        RES_OPTIONS,
                        default_value=RES_OPTIONS[3],
                        key="resolution",
                        enable_events=True,
                    ),
                ],  # default to 720p
                [sg.Text("FPS"), sg.InputText("30", size=(5, 1), key="fps", enable_events=True)],
            ],
        ),
        sg.Text("", key="res_warning", text_color="red", metadata={"reso_y": 10000, "fuhpis": 1000})
    ],
    [
        sg.Button(
            "✅Start",
            key="start",
        ),
        sg.Button("❌Cancel", key="cancel"),
    ],
    [
        sg.ProgressBar(100, orientation="h", size=(20, 20), key="progressbar"),
        sg.Text("Click 'Start' to start  :   |", key="status"),
    ],
]

# Create the Window
window = sg.Window("Clippy", layout, icon=SCISSORS_ICON, finalize=True)


def get_clip_length_text(start_time, end_time):
    """get clip length text"""
    clip_length = end_time - start_time
    print(clip_length, start_time, end_time)
    if clip_length == 0:
        return "red", "Clip is zero seconds long!"
    elif clip_length < 0:
        return "red", "End time is before start time!"
    return "black", f"Clip length: {tc.get_time(clip_length)}"


def update_clip_length_text(window):
    _, values = window.read(timeout=1)  # have to update the values
    color, clip_len = get_clip_length_text(
        values["start_time_slider"], values["end_time_slider"]
    )
    window["clip_length"].update(clip_len, text_color=color)
    # do not allow end time to be before start time
    if color == "red":
        window["start"].update(disabled=True)
    else:
        window["start"].update(disabled=False)


def get_status_text(progress, done=False):
    """get status text"""
    if done:
        return "Status: Press 'Start' to start  :   |"
    return f"Status: Clipping {progress:.2f}%  :   O"


def update_res_warning(window):
    _, values = window.read(timeout=1)  # have to update the values
    selected_reso_y = int(values["resolution"].split("p")[0])
    selected_fuhpis = int(values["fps"])
    source_reso_y = window["res_warning"].metadata["reso_y"]
    source_fuhpis = window["res_warning"].metadata["fuhpis"]
    builder = ""
    if selected_reso_y > source_reso_y:
        builder += f"{selected_reso_y}p is higher than source {source_reso_y}p.\n"
    if selected_fuhpis > source_fuhpis:
        builder += f"{selected_fuhpis:g} FPS is higher than source video ({source_fuhpis:g})."
    if builder == "":
        window["res_warning"].update("")
    else:
        builder = "Export settings are not ideal.\nThese settings may cause large file sizes:\n" + builder
        window["res_warning"].update(builder)


def show_custom_error(message, title="Oops!"):
    sg.popup_error(message, title=title, icon=SCISSORS_ICON)


def show_custom_yesno(message, title="Hol up"):
    return sg.popup_yes_no(message, title=title, icon=SCISSORS_ICON, grab_anywhere=True)


def done_message(output_file):
    # look up file size
    try:
        bytesize = os.path.getsize(output_file)
        textsize = humanize.naturalsize(bytesize, binary=True)
        fits_on_discord = bytesize < DISCORD_LIMIT
    except FileNotFoundError:
        textsize = None

    add_string = f"\nSize of clip: {textsize}"
    if textsize is None:
        add_string = ""
    elif not fits_on_discord:
        add_string += "\n\nThis file is too big to send on Discord.\nTry lowering the resolution or FPS."
    sg.popup_ok(f"Done!{add_string}", title="Done!", icon=SCISSORS_ICON)


just_clipped = None

# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event in (None, "cancel"):  # if user closes window or clicks cancel
        break
    elif event == "start":
        if values["input_file"] == "":
            show_custom_error("Please choose a file to clip using the 'Browse' button.")
            continue
        if values["output_file"] == "":
            show_custom_error("Please set an output using the 'Save As' button.")
            continue
        if values["input_file"] == values["output_file"]:
            show_custom_error("Input and output files cannot be the same.")
            continue
        if values["fps"] == "0":
            show_custom_error("FPS must be more than 0.")
            continue

        if just_clipped == values["output_file"]:
            if not show_custom_yesno("You didn't change the output file name.\nAre you sure you want to overwrite the file?"):
                continue
        # send values to construct ffmpeg command
        cmd = fp.construct_from_sg_values(values)
        # replace ffmpeg location
        cmd[0] = FFMPEG_LOC
        # run ffmpeg command yielding progress
        duration = values["end_time_slider"] - values["start_time_slider"]
        window.perform_long_operation(
            lambda: fp.run_yielding_ffmpeg(cmd, window, duration),
            end_key="ffmpeg_done",
        )
        # break

    # update slider ranges on input file change
    if event == "input_file":
        try:
            probe = ffmpeg.probe(values["input_file"], cmd=FFPROBE_LOC, popen_kwargs={"creationflags": CREATE_NO_WINDOW})
        except ffmpeg.Error as e:
            sg.popup_error(e.stderr)
            continue
        # window["input_file"].update(values["input_file"])
        duration = probe["format"]["duration"]
        duration = float(duration)
        # assign resolution metadata to warning
        frame_numer, frame_denom = probe["streams"][0]["r_frame_rate"].split("/")
        frame_numer = int(frame_numer)
        frame_denom = int(frame_denom)
        official_fps = frame_numer / frame_denom
        window["res_warning"].metadata = {
            "reso_y": probe["streams"][0]["height"],
            "fuhpis": official_fps,
        }
        window["start_time_slider"].update(range=(0, duration))
        window["end_time_slider"].update(range=(0, duration))
        window["end_time_slider"].update(value=duration)
        window["end_time_input"].update(tc.get_time(duration))
        # update clip length
        update_clip_length_text(window)
        # check resolution warning
        update_res_warning(window)

    # checking controls
    if event == "start_time_slider":
        text = tc.get_time(values["start_time_slider"])
        window["start_time_input"].update(text)
        update_clip_length_text(window)
    if event == "end_time_slider":
        text = tc.get_time(values["end_time_slider"])
        window["end_time_input"].update(text)
        update_clip_length_text(window)

    # check time input boxes
    if event == "start_time_input":
        # if error during conversion, pass until time is valid
        try:
            sec = tc.get_sec(values["start_time_input"])
        except ValueError:
            continue
        window["start_time_slider"].update(sec)
        update_clip_length_text(window)
    if event == "end_time_input":
        try:
            sec = tc.get_sec(values["end_time_input"])
        except ValueError:
            continue
        window["end_time_slider"].update(sec)
        update_clip_length_text(window)

    # check resolution warning
    if event == "resolution" or event == "fps":
        if values["fps"] == "":
            window["fps"].update("0")
        update_res_warning(window)

    # if progress is made
    if event == "ffmpeg_progress":
        window["progressbar"].update(values["ffmpeg_progress"])
        window["status"].update(get_status_text(values["ffmpeg_progress"]))
        continue

    # if ffmpeg is done
    if event == "ffmpeg_done":
        window["status"].update(get_status_text(0, True))
        window["progressbar"].update(0)
        window["start"].update(disabled=False)
        done_message(values["output_file"])
        just_clipped = values["output_file"]
        # break

    print(event)
    print(values)
