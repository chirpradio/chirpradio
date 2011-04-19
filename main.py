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

"""Bootstrap for running a Django app under Google App Engine.

The site-specific code is all in other files: settings.py, urls.py,
models.py, views.py.  And in fact, only 'settings' is referenced here
directly -- everything else is controlled from there.

"""

# Standard Python imports.
import os
import sys
import logging

ROOT = os.path.dirname(__file__)

from appengine_django import InstallAppengineHelperForDjango
InstallAppengineHelperForDjango('1.2')

# Import the part of Django that we use here.
import django.core.handlers.wsgi

# Map the contents of the django-extras tree into the django
# module's namespace.
import django
django.__path__.append(os.path.join(ROOT, 'django-extras'))

# Pull in CHIRP's monkey-patching of Django
from django import _monkey_patch

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Create a Django application for WSGI.
application = django.core.handlers.wsgi.WSGIHandler()

def main():
    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()