"""Stubbed-out versions of django.contrib.auth functions.

Some parts of core Django (like the testing system) depend on
django.contrib.auth.  Here we put in a few stub APIs, just enough to
keep the imports from failing.
"""

from auth.models import User

def authenticate(**credentials):
    raise NotImplementedError


def login(request, user):
    raise NotImplementedError
