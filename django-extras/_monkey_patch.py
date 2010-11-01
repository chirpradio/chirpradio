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

"""Monkey-patching for Django.

These are CHIRP-specific hacks that make Django 1.0 behave the way we want.
"""

from django.test import client
import auth
from auth.models import User


###
### Replaces Client.login and Client.logout with versions that
### support our custom authentication.
###

def chirp_Client_login(self, **credentials):
    """If the given credentials are valid, return a User object."""
    user = None
    email = credentials.get('email')
    if email:
        user = User.get_by_email(email)
        if user is None:
            user = User(email=email)
        for key, value in credentials.items():
            setattr(user, key, value)
        user.save()

    token = ''
    if user:
        token = auth._create_security_token(user)
    self.cookies[auth._CHIRP_SECURITY_TOKEN_COOKIE] = token
    if token:
        return True


def chirp_Client_logout(self):
    del self.cookies[auth._CHIRP_SECURITY_TOKEN_COOKIE]


client.Client.login = chirp_Client_login
client.Client.logout = chirp_Client_logout
