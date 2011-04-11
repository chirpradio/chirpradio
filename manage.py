#!/usr/bin/env python2.5
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# WARNING: This script is not run in production.
# See main.py for that.

# installs app engine django
import main

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)


if __name__ == "__main__":

    # chirp: hack to enable testlib.
    import glob
    import sys
    import os
    if 'test' in sys.argv:
        testlib = os.path.join(os.path.dirname(__file__), 'testlib')
        if not os.path.exists(testlib):
            raise EnvironmentError("Expected lib dir to exist: %r" % testlib)
        for path in glob.glob(testlib+'/*.zip'):
            mod = os.path.splitext(os.path.basename(path))[0]
            # e.g. /path/to/fudge-0.9.4.zip/fudge-0.9.4
            sys.path.append(os.path.join(path, mod))

    execute_manager(settings)
