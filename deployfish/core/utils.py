from typing import Optional
import re


def is_fnmatch_filter(f: Optional[str]) -> bool:
    if f is not None and re.search(r'[\[?*]', f):
        return True
    return False
