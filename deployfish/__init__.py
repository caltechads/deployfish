from cement.utils.version import get_version as cement_get_version

#: Version.
VERSION = (1, 16, 2, "final", 0)


def get_version(version=VERSION):
    """
    Get version.

    Args:
        version: version.

    Returns:
        Operation result.

    """
    return cement_get_version(version)
