CURRENT = "1.2.9"
CHANGES = """
(1.2.9) Use more efficient HEVC format. Should make smaller file sizes.
Fix bug where "Done!" message wouldn't show output file size.
Update Discord file size limit (fuck discord).

(1.2.8) Small facelift. Fixed some crashes.

(1.2.4) Start and end time sliders can now be scrolled with the mouse wheel.

"""

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
1.1.6 = forgot to make it stop if fps is not a digit
todo: maybe make resolution/fps check adjust the settings to the most ideal for the current file
1.2.0 = added support for audio files; refactored main loop and data validation; added auto resolution button; refactor ffprobe process
1.2.1 = add gpu detection and encoder choice, if nvidia gpu is present
1.2.2 = idk
1.2.3 = add "remux" option for encoder bc i need mkv's to be mp4's

todo: add automatic updates so i don't have to send a whole file over discord to people every single time
"""

"""old versions
(1.2.0) Added support for clipping audio files.
Refactored data validation and main event loop.
Added auto resolution/FPS button.
Added GPU detection and encoder choice for NVENC.
Make "Done!" message box go away on its own.

(1.1.6) Check for special characters in filename now obeys Windows filename rules.
Added this About window.
Refactored settings file save/load.
Saving is more robust on window close.
Fixed crash when non-numeric characters typed in FPS box.
Fixed an error when clipping a video with a resolution not divisible by 2.
Added error handling for missing binaries.
Fixed the previous fix for the FPS box. FPS box now only accepts numbers."""