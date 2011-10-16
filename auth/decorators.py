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

"""Decorators for CHIRP's authentication system."""

from django import http
import auth
from auth import models


class require_role(object):
    """A decorator that limits access only to users with a particular role.

    If 'role' is None, this check is pass for any signed-in user.
    """
    def __init__(self, role, logic=0):
        if role is None or type(role) is list:
            self._role = role
        else:
            self._role = [role]
        self._logic = logic

    def __call__(self, func):
        def wrapper(request, *args, **kwargs):
            # Not signed in?  Redirect to a login page.
            if not request.user:
                return http.HttpResponseRedirect(
                    auth.create_login_url(request.path))
            # If the user is signed in and has the required role(s),
            # satisfy the request.
            allow = False
            if self._role is None or (request.user and
                                      request.user.is_superuser):
                allow = True
            if not allow:
                for role in self._role:
                    if role in request.user.roles:
                        if self._logic == 0:
                            allow = True
                            break
                        else:
                            allow = True
                    elif self._logic == 1:
                        allow = False
                        break
            if allow:
                return func(request, *args, **kwargs)
            else:
                # Return a 403.
                s = 'Page requires '
                if len(self._role) > 1:
                    if self._logic == 0:
                        s += 'any '
                    else:
                        s += 'all '
                    s += 'roles '
                else:
                    s += 'role '
                s += '"%s"' % '", "'.join(self._role)
                return http.HttpResponseForbidden(s)
        return wrapper


def require_signed_in_user(func):
    """A decorator that limits access to signed-in users.

    Note that limiting acces to signed-in users is the default
    behavior for all pages outside of the /auth/ namespace.
    """
    def wrapper(request, *args, **kwargs):
        if getattr(request, 'user') is None:
            # If the user is not signed in, send them off to somewhere
            # they can log in.
            login_url = auth.create_login_url(request.path)
            return http.HttpResponseRedirect(login_url)
        return func(request, *args, **kwargs)
    return wrapper
