import ffmpeg
import ffmpeg_progress_yield as fpy
from subprocess import CREATE_NO_WINDOW


class NoStreamsFoundException(Exception):
    pass


class TooManyStreamsException(Exception):
    pass


current_ff = None


def construct_from_sg_values(values):
    """Constructs ffmpeg command from values dictionary.

    Args:
        values (dict): Dictionary of values from PySimpleGUI window.

    Returns:
        list: ffmpeg command as list of strings.
    """
    reso = values["resolution"]
    reso_y = reso.split("p")[0]
    fps = values["fps"]
    audio_only = values["audio_only"]
    enc = values["encoder_combo"]

    if "CPU" in enc:
        enc = "libx265"
    elif "NVENC" in enc:
        enc = "hevc_nvenc"
    elif "Remux" in enc:
        enc = "copy"

    input = ffmpeg.input(
        values["input_file"],
        ss=values["start_time_slider"],
        to=values["end_time_slider"],
    )

    audio = input.audio

    output = None

    if not audio_only and not enc == "copy":
        video = input.video
        scale = video.filter(
            "scale", -2, reso_y
        )  # -1 means keep aspect ratio, reso_y is progressive fields (aka 1080p for example)

        output = ffmpeg.output(
            scale,
            audio,
            values["output_file"],
            **{"c:v": enc, "r": fps},
        )
    elif audio_only:
        output = ffmpeg.output(
            audio,
            values["output_file"],
        )
    else:  # remuxing
        input = ffmpeg.input(values["input_file"], )
        output = ffmpeg.output(
            input,
            values["output_file"],
            **{"map": "0", "c:v": "copy", "c:a": "copy", "c:s": "copy"},
        )

    if output is None:
        # literally how?
        raise AssertionError("how is output equal to none in ffmpeg_processor?")

    output = ffmpeg.overwrite_output(output)

    command = output.compile()

    # replace "0:a" with "0:a?" for ambiguous audio stream mapping
    command = [x.replace("0:a", "0:a?") for x in command]

    return command


def run_yielding_ffmpeg(cmd, window, duration):
    global current_ff
    """Runs ffmpeg command yielding progress.

    Args:
        window (PySimpleGUI.Window): PySimpleGUI window object.
        window (None): Yield percentage as a float.

    Yields:
        float: Progress percentage.
    """
    current_ff = fpy.FfmpegProgress(cmd)
    for progress in current_ff.run_command_with_progress(
        popen_kwargs={"creationflags": CREATE_NO_WINDOW}, duration_override=duration
    ):
        if window is None:
            yield progress
        else:
            window.write_event_value("ffmpeg_progress", progress)

    current_ff = None


def cancel_current_ffmpeg():
    global current_ff
    """Cancels the current FFMPEG process."""
    if current_ff is not None:
        current_ff.quit_gracefully()


# ffprobe things


def get_file_info(file, ffprobe_loc):
    """Get file info from ffprobe.

    Args:
        file (str): File path.

    Returns:
        dict: File info.
    """
    try:
        probe = ffmpeg.probe(
            file,
            cmd=ffprobe_loc,
            popen_kwargs={"creationflags": CREATE_NO_WINDOW},
            v="error",
        )
    except ffmpeg.Error as e:
        raise e
    return probe


def parse_ffprobe_info(probe):
    """Parse ffprobe info.

    Args:
        probe (dict): ffprobe info.

    Returns:
        dict: Parsed info.
    """

    if "streams" not in probe:
        raise NoStreamsFoundException("No streams found in file.")

    if len(probe["streams"]) == 0:
        raise NoStreamsFoundException("No streams found in file.")

    has_video = False
    for stream in probe["streams"]:
        if stream["codec_type"] == "video":
            has_video = True
            video_stream_idx = stream["index"]
            break

    duration = probe["format"]["duration"]
    duration = float(duration)

    if has_video:
        frame_numer, frame_denom = probe["streams"][video_stream_idx]["r_frame_rate"].split("/")  # fmt: skip
        frame_numer = int(frame_numer)
        frame_denom = int(frame_denom)
        official_fps = frame_numer / frame_denom
    else:
        official_fps = None

    info = {
        "audio_only": not has_video,
        "reso_y": (
            None if not has_video else probe["streams"][video_stream_idx]["height"]
        ),
        "fps": None if not has_video else official_fps,
        "duration": duration,
    }

    return info
