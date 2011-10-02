import glob
import os
import sys


def activate():
    """Adds sys.paths for all zipped Python modules in the devlib dir.

    NOTE: this is intended for local development and testing, not
    for use on App Engine.
    """
    devlib = os.path.join(os.path.dirname(__file__), 'devlib')
    if not os.path.exists(devlib):
        raise EnvironmentError("Expected lib dir to exist: %r" % devlib)
    for path in glob.glob(devlib+'/*.zip'):
        mod = os.path.splitext(os.path.basename(path))[0]
        # e.g. /path/to/fudge-0.9.4.zip/fudge-0.9.4
        sys.path.append(os.path.join(path, mod))
