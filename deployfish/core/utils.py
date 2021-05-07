import re


def is_fnmatch_filter(f):
    if f is not None and re.search(r'[\[?*]', f):
        return True
    return False
