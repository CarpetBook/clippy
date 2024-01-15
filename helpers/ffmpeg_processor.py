import ffmpeg
import ffmpeg_progress_yield as fpy
from subprocess import CREATE_NO_WINDOW


def construct_from_sg_values(values):
    """Constructs ffmpeg command from values dictionary.

    Args:
        values (dict): Dictionary of values from PySimpleGUI window.

    Returns:
        list: ffmpeg command as list of strings.
    """
    reso = values["resolution"]
    reso_y = reso.split("p")[0]
    fuhpis = values["fps"]

    input = ffmpeg.input(
        values["input_file"],
        ss=values["start_time_slider"],
        to=values["end_time_slider"],
    )

    audio = input.audio
    video = input.video

    scale = video.filter(
        "scale", -1, reso_y
    )  # -1 means keep aspect ratio, reso_y is progressive fields (aka 1080p for example)
    output = ffmpeg.output(
        scale,
        audio,
        values["output_file"],
        **{"c:v": "libx264", "r": fuhpis},
    )
    output = ffmpeg.overwrite_output(output)

    return output.compile()


def run_yielding_ffmpeg(cmd, window, duration):
    """Runs ffmpeg command yielding progress.

    Args:
        window (PySimpleGUI.Window): PySimpleGUI window object.

    Yields:
        int: Progress percentage.
    """
    ff = fpy.FfmpegProgress(cmd)
    for progress in ff.run_command_with_progress(popen_kwargs={"creationflags": CREATE_NO_WINDOW}, duration_override=duration):
        window.write_event_value("ffmpeg_progress", progress)
