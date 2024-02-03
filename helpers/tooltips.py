tooltips = {
    "audio_to_video_check": "Audio will have an image added to it to create a video.",
}


def tooltip(tip_id):
    return tooltips[tip_id] if tip_id in tooltips else None
