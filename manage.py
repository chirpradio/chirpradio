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
import os
import sys

# WARNING: This script is not run in production.
# See main.py for that.

# manage.py is only used for testing.
# This will set a flag so that main.py knows we are testing
os.environ['IN_MANAGE'] = '1'

# Install the old app engine *only* for testing.
# This sets up datastore stubs and clears data.
from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango('1.3')

# Loads the production app.
import main

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)


if __name__ == "__main__":

    # chirp: hack to enable devlib.
    if 'test' in sys.argv:
        import devlib
        devlib.activate()
    else:
        raise NotImplementedError('Use dev_appserver.py for non-test '
                                  'commands.')

    execute_manager(settings)
