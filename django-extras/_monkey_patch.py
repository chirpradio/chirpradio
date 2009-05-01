
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

def fake_Client_login(self, **credentials):
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


def fake_Client_logout(self):
    del self.cookies[auth._CHIRP_SECURITY_TOKEN_COOKIE]


client.Client.login = fake_Client_login
client.Client.logout = fake_Client_logout
