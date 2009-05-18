###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

"""Stubbed-out versions of django.contrib.auth functions.

Some parts of core Django (like the testing system) depend on
django.contrib.auth.  Here we put in a few stub APIs, just enough to
keep the imports from failing.
"""


def authenticate(**credentials):
    raise NotImplementedError


def login(request, user):
    raise NotImplementedError
