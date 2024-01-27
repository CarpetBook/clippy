CURRENT = "1.1.5"
CHANGES = "Added error handling for missing binaries.\nFixed an error when clipping a video with a resolution not divisible by 2."

"""
1.0 = first clippy release
1.0.1 = clippy with smaller ffmpeg/probe
1.0.3 = added confirmation for overwriting file

1.1 = added save folder instead of save path; settings.txt for saving values; exception "handling" for ffmpeg errors; handle possible missing audio streams
1.1.1 = fixed broken special character check in filename
1.1.2 = added about window
todo: the settings saving and loading is really really bad. very hard coded. refactor very soon
1.1.3 = fixed the saving; uses json like yts now
1.1.4 = checked for non-numbers in fps on start, but not on event... fixed to ignore on letters in fps; converted changelog to py file to compile into exe
1.1.5 = fixed scaling in ffmpeg when resolution is not divisible by 2; added a check for ffmpeg/probe not being found

todo: add automatic updates so i don't have to send a whole file over discord to people every single time
"""
