"""
time calculation helpers

calculating string time from second input from ffprobe
"""


def get_sec(time_str):
    """get seconds from time"""
    terms = time_str.split(":")
    if len(terms) == 3:
        h, m, s = terms
    elif len(terms) == 2:
        h = 0
        m, s = terms
    else:
        h = 0
        m = 0
        s = terms[0]
    return float(h) * 3600 + float(m) * 60 + float(s)


def get_time(sec):
    """get time from seconds"""
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h == 0 and m == 0:
        return "%06.3f" % s
    elif h == 0:
        return "%02d:%06.3f" % (m, s)
    else:
        return "%02d:%02d:%06.3f" % (h, m, s)
