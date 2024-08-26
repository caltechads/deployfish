from typing import Optional
import re


def is_fnmatch_filter(f: Optional[str]) -> bool:
    """
    Use this function to determine if a string is a fnmatch filter, which
    is to say glob pattern.  We determine this by checking for the presence
    of any of the following characters: '[', '?', or '*'.

    Args:
        f: The string to check for glob pattern.

    Returns:
        ``True`` if the string is a glob pattern, ``False`` otherwise.
    """
    if f is not None and re.search(r'[\[?*]', f):
        return True
    return False
