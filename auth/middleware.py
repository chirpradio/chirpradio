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

"""Middleware for CHIRP's authentication system."""

from django import http
import auth


class AuthenticationMiddleware(object):

    def process_request(self, request):
        try:
            user = auth.get_current_user(request)
        except auth.UserNotAllowedError:
            return http.HttpResponseForbidden('Access Denied!')
        # Un-logged-in users are not redirected away from the /auth/
        # namespace.  This ensures that the log-in and related pages
        # are reachable.
        if user is None and not request.path.startswith('/auth/'):
            login_url = auth.create_login_url(request.path)
            return http.HttpResponseRedirect(login_url)
        # Attach the user to the request.
        request.user = user
        return None

    def process_response(self, request, response):
        # If the "_logout" flag is set on the response, generate a response
        # that will log the user out.
        if getattr(response, '_logout', False):
            return auth.logout()
        # If our security token is old, issue a new one.
        if hasattr(request, 'user'):
            cred = getattr(request.user, '_credentials', None)
            if cred and cred.security_token_is_stale:
                auth.attach_credentials(response, request.user)
        return response
