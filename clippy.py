import PySimpleGUI as sg

import os
import re
import humanize
import json

from ffmpeg import Error as FfmpegError

from helpers import timecalc as tc
from helpers import ffmpeg_processor as fp
from helpers import icon
from helpers.about_window import open_about_window

from helpers.tooltips import tooltip

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

ffmpeg_loc = "bin/ffmpeg.exe"
ffprobe_loc = "bin/ffprobe.exe"
SCISSORS_ICON = icon.SCISSORS_ICON

SPECIAL_CHAR_CHECK = r"[<>:""/\\|?*]"

DISCORD_LIMIT = 25 * 1024 * 1024


builtindefaults = {
    "clip_loc": "",
    "resolution": RES_OPTIONS[3],
    "fps": "30",
}


def write_new_settings():
    with open("settings.json", "w") as f:
        f.write(json.dumps(builtindefaults, indent=4))


"""Read settings file."""
try:
    with open("settings.json", "r") as f:
        defaults = json.loads(f.read())

    # check if all are valid
    if not os.path.exists(defaults.get("clip_loc", "")):
        defaults["clip_loc"] = ""

    if defaults.get("resolution") not in RES_OPTIONS:
        defaults["resolution"] = RES_OPTIONS[3]

    if not defaults.get("fps").isdigit():
        defaults["fps"] = "30"
except Exception as e:
    print(e)
    write_new_settings()
    defaults = builtindefaults


def save_settings(values):
    """Save settings to settings.json."""
    with open("settings.json", "w") as f:
        f.write(json.dumps(values, indent=4))


# All the stuff inside your window.
layout = [
    [
        sg.Text("File to be clipped", size=(15, 1)),
        sg.InputText(key="input_file", disabled=True, enable_events=True),
        sg.FileBrowse("Browse"),
    ],
    [
        sg.Text("Save folder", size=(15, 1)),
        sg.InputText(key="clip_loc", default_text=defaults.get("clip_loc")),
        sg.FolderBrowse("Browse"),
    ],
    [
        sg.Text("File name", size=(15, 1)),
        sg.InputText(key="output_file"),
    ],
    [sg.Text("")],
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
                # [
                #     sg.Checkbox("Export as audio only", key="audio_only_check", enable_events=True),
                # ],
                [
                    sg.Text("Resolution", key="reso_label"),
                    sg.Combo(
                        RES_OPTIONS,
                        default_value=defaults.get("resolution"),
                        key="resolution",
                        enable_events=True,
                    ),
                    # # only visible when attaching image to audio
                    # sg.Checkbox(
                    #     "Turn audio into video",
                    #     key="audio_to_video_check",
                    #     visible=False,
                    #     default=defaults.get("audio_to_video_check"),
                    #     enable_events=True,
                    #     tooltip=tooltip("audio_to_video_check"),
                    # ),
                ],  # default to 720p
                [
                    sg.Text("FPS", key="fps_label"),
                    sg.InputText(
                        defaults.get("fps"), size=(5, 1), key="fps", enable_events=True
                    ),
                    # only visible when audio_to_video_check is checked
                    sg.Text("Audio output", key="container_label", visible=False),
                    sg.Combo(
                        AUD_CONTAINERS,
                        default_value=defaults.get("export_container"),
                        key="export_container",
                        visible=False,
                        enable_events=True,
                    ),
                    # # only visible when audio_to_video_check is checked
                    # sg.Text("Image to attach", key="image_label", visible=False),
                    # sg.InputText(
                    #     key="image_to_attach",
                    #     visible=False,
                    #     size=(15, 1),
                    # ),
                    # sg.FileBrowse("Browse", key="browse_image", visible=False),
                ],
            ],
        ),
        sg.Text(
            "",
            key="res_warning",
            text_color="red",
            metadata={"reso_y": 10000, "fps": 1000},
        ),
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
        sg.Push(),
        sg.Button("?", key="about"),
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
    try:
        selected_fps = int(values["fps"])
    except ValueError:
        selected_fps = 0
    source_reso_y = window["res_warning"].metadata["reso_y"]
    source_fps = window["res_warning"].metadata["fps"]
    if source_reso_y is None or source_fps is None:
        window["res_warning"].update("")
        return
    builder = ""
    if selected_reso_y > source_reso_y:
        builder += f"{selected_reso_y}p is higher than source {source_reso_y}p.\n"
    if selected_fps > source_fps:
        builder += f"{selected_fps:g} FPS is higher than source video ({source_fps:g})."
    if builder == "":
        window["res_warning"].update("")
    else:
        builder = (
            "Export settings are not ideal.\nThese settings may cause large file sizes:\n" + builder  # fmt: skip
        )
        window["res_warning"].update(builder)


def toggle_export_options(window, audio_only):
    """Toggle export options."""
    # hide resolution and fps if audio
    window["reso_label"].update(visible=not audio_only)
    window["resolution"].update(visible=not audio_only)
    window["fps_label"].update(visible=not audio_only)
    window["fps"].update(visible=not audio_only)

    # hide auto res button
    window["auto_res"].update(visible=not audio_only)

    # show audio containers and audio_to_video_check
    window["container_label"].update(visible=audio_only)
    window["export_container"].update(visible=audio_only)
    # window["audio_to_video_check"].update(visible=audio_only)

    # disable audio container if audio to video
    # audio_to_video = window["audio_to_video_check"].get()
    # window["export_container"].update(disabled=audio_to_video)


def toggle_attach_image(audio_to_video):
    """Toggle attach image."""
    # hide audio container
    window["container_label"].update(visible=not audio_to_video)
    window["export_container"].update(visible=not audio_to_video)

    # show image to attach options
    window["image_label"].update(visible=audio_to_video)
    window["image_to_attach"].update(visible=audio_to_video)
    window["browse_image"].update(visible=audio_to_video)


def update_extension_on_format(window, values):
    """Update extension on format change."""
    if values["output_file"].split(".")[-1] in AUD_CONTAINERS + ["mp4"]:
        # replace extension
        new_output_file = (  # this code is fugly
            ".".join(values["output_file"].split(".")[:-1]) + f".{values['export_container']}"  # fmt: skip
        )
        window["output_file"].update(new_output_file)
        return

    if not values["output_file"].endswith(values["export_container"]):
        window["output_file"].update(
            values["output_file"] + "." + values["export_container"]
        )
        return

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


def run_yielding_ffmpeg_exc(cmd, window, duration):
    """Runs run_yielding_ffmpeg and catches RuntimeError (ffmpeg yield progress throws runtime error for some reason)."""
    try:
        fp.run_yielding_ffmpeg(cmd, window, duration)
    except RuntimeError as e:
        show_custom_error(e)
        window.write_event_value("ffmpeg_done", "error")
        return


def check_for_ffmpeg():
    global ffmpeg_loc
    if os.path.exists(ffmpeg_loc):
        return
    if os.path.exists("ffmpeg.exe"):
        ffmpeg_loc = "ffmpeg.exe"
        return
    show_custom_error("Couldn't find ffmpeg.exe. Please make sure you extracted the 'bin' folder into the same folder as clippy.exe.")
    exit(1)


def check_for_ffprobe():
    global ffprobe_loc
    if os.path.exists(ffprobe_loc):
        return
    if os.path.exists("ffprobe.exe"):
        ffprobe_loc = "ffprobe.exe"
        return
    show_custom_error("Couldn't find ffprobe.exe. Please make sure you extracted the 'bin' folder into the same folder as clippy.exe.")
    exit(1)


def check_for_fftools():
    check_for_ffmpeg()
    check_for_ffprobe()


just_clipped = None
last_values = defaults
input_audio_only_or_extract_audio = False


def main_app():
    global just_clipped, last_values, input_audio_only_or_extract_audio
    # main window event loop
    while True:
        event, values = window.read()
        print(values)
        if values is not None:
            last_values = values

        if event in (None, "cancel"):  # if user closes window or clicks cancel
            save_settings(last_values)
            break

        elif event == "start":
            _ok = start_data_validation(values)
            if not _ok:
                continue

            was_just_clipped = (
                just_clipped == values["output_file"] + "." + values["export_container"]
            )
            already_exists = os.path.exists(
                os.path.join(values["clip_loc"], values["output_file"])
            )
            if was_just_clipped or already_exists:
                ans = show_custom_yesno(
                    "This file already exists in the save folder.\nAre you sure you want to overwrite the file?"
                )
                if ans == "No" or ans is None:
                    continue

            # check if file name has extension
            # if not, add it
            _extension = (
                values["export_container"]
                if input_audio_only_or_extract_audio
                else "mp4"
            )
            if not values["output_file"].endswith(_extension):
                values["output_file"] += f".{_extension}"
            # correct output file path with clip_loc
            values["output_file"] = os.path.join(
                values["clip_loc"], values["output_file"]
            )
            # send values to construct ffmpeg command
            # add audio_only flag
            values["audio_only"] = input_audio_only_or_extract_audio
            cmd = fp.construct_from_sg_values(values)
            # replace ffmpeg location
            cmd[0] = ffmpeg_loc
            # run ffmpeg command yielding progress
            duration = values["end_time_slider"] - values["start_time_slider"]
            window.perform_long_operation(
                lambda: run_yielding_ffmpeg_exc(cmd, window, duration),
                end_key="ffmpeg_done",
            )
            # break

        # update slider ranges on input file change
        if event == "input_file":
            try:
                probe = fp.get_file_info(values["input_file"], ffprobe_loc)
                info = fp.parse_ffprobe_info(probe)
                # store info in input file box
                window["input_file"].metadata = info

                # if audio only
                window["resolution"].update(disabled=info["audio_only"])
                input_audio_only_or_extract_audio = info["audio_only"]

                window["res_warning"].metadata = {
                    "reso_y": info["reso_y"],
                    "fps": info["fps"],
                }
                duration = info["duration"]
                window["start_time_slider"].update(range=(0, duration))
                window["end_time_slider"].update(range=(0, duration))
                window["end_time_slider"].update(value=duration)
                window["end_time_input"].update(tc.get_time(duration))
            except fp.NoStreamsFoundException as e:
                _er_str = "Input file seems to be empty:\n" + str(e)
                show_custom_error(_er_str)
                window["input_file"].update("")
                continue
            except FfmpegError as e:
                _er_str = "Input file seems to be broken:\n" + str(e.stderr, "utf-8")
                show_custom_error(_er_str)
                window["input_file"].update("")
                continue
            except Exception as e:
                _er_str = "Error opening input file:\n" + str(e)
                show_custom_error(_er_str)
                window["input_file"].update("")
                continue
            # update clip length
            update_clip_length_text(window)
            # check resolution warning
            update_res_warning(window)
            # is audio only? if so, disable resolution
            toggle_export_options(window, input_audio_only_or_extract_audio)
            # set clip file name
            filey = os.path.basename(values["input_file"])
            filey = os.path.splitext(filey)[0]
            container_ext = (
                values["export_container"]
                if input_audio_only_or_extract_audio
                else "mp4"
            )
            window["output_file"].update(filey + f"_clippy.{container_ext}")

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
            # start process will check for valid time
            sec = is_time_valid(values["start_time_input"])
            if sec is False:
                continue
            window["start_time_slider"].update(sec)
            update_clip_length_text(window)
        if event == "end_time_input":
            sec = is_time_valid(values["end_time_input"])
            if sec is False:
                continue
            window["end_time_slider"].update(sec)
            update_clip_length_text(window)

        # check resolution warning
        if event == "resolution" or event == "fps":
            if values["fps"] == "":
                window["fps"].update("0")
            update_res_warning(window)

        # update extension on format change
        if event == "export_container":
            update_extension_on_format(window, values)

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
            if values["ffmpeg_done"] == "error":
                continue
            joined_path = os.path.join(values["clip_loc"], values["output_file"])
            done_message(joined_path)
            just_clipped = values["output_file"] + "." + values["export_container"]
            # break

        # if audio_to_video_check is checked
        if event == "audio_to_video_check":
            toggle_export_options(window, input_audio_only_or_extract_audio)
            toggle_attach_image(values["audio_to_video_check"])

        # if audio_only_check is checked
        if event == "audio_only_check":
            input_audio_only_or_extract_audio = values["audio_only_check"]
            toggle_export_options(window, input_audio_only_or_extract_audio)

        # if about button is pressed
        if event == "about":
            open_about_window()

    print(event)
    print(values)

        print(event)
        print(values)


if __name__ == "__main__":
    check_for_fftools()
    main_app()
