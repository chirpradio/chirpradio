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

"""CHIRP authentication system."""

import base64
import logging
import os
import time

from common import in_prod
from common.autoretry import AutoRetry

# TODO(trow): This is a work-around for problems with PyCrypto on the Mac.
# For more information, see
# http://code.google.com/p/googleappengine/issues/detail?id=1627
_DISABLE_CRYPTO = False
try:
    from Crypto.Cipher import AES
    from Crypto.Hash import HMAC
except ImportError:
    # Only allow crypto to be disabled if we are running in a local
    # development environment.
    if in_prod():
        raise
    _DISABLE_CRYPTO = True
    logging.warn("PyCrypto not found!  Operating in insecure mode!")
    
from django import http
from auth.models import User, KeyStorage
from auth import roles

# Our logout URL.
LOGOUT_URL = "/auth/goodbye/"

# Users are ultimately redirected to the URL after logging out.
_FINAL_LOGOUT_URL = '/auth/hello/'

# The name of the cookie used to store our security token.
_CHIRP_SECURITY_TOKEN_COOKIE = 'chirp_security_token'

# Our security tokens expire after 24 hours.
# TODO(kumar) set this back to two hours after 
# all CHIRP volunteers have set initial password?
_TOKEN_TIMEOUT_S = 24 * 60 * 60


class UserNotAllowedError(Exception):
    """Raised when the user is recognized but forbidden from entering."""


class _Credentials(object):
    email = None
    security_token_is_stale = False


def _create_security_token(user):
    """Create a CHIRP security token.

    Args:
      user: A User object.

    Returns:
      A string containing an encrypted security token that encodes
      the user's email address as well as a timestamp.
    """
    timestamp = int(time.time())
    plaintext = "%x %s" % (timestamp, user.email)
    nearest_mult_of_16 = 16 * ((len(plaintext) + 15) // 16)
    # Pad plaintest with whitespace to make the length a multiple of 16,
    # as this is a requirement of AES encryption.
    plaintext = plaintext.rjust(nearest_mult_of_16, ' ')
    if _DISABLE_CRYPTO:
        body = plaintext
        sig = "sig"
    else:
        key_storage = KeyStorage.get()
        body = AES.new(key_storage.aes_key, AES.MODE_CBC).encrypt(plaintext)
        hmac_key = key_storage.hmac_key
        if type(hmac_key) == unicode:
            # Crypto requires byte strings
            hmac_key = hmac_key.encode('utf8')
        sig = HMAC.HMAC(key=hmac_key, msg=body).hexdigest()
    return '%s:%s' % (sig, body)

def _parse_security_token(token):
    """Parse a CHIRP security token.

    Returns:
      A Credentials object, or None if the token is not valid.
      If a Credentials object is returned, its "user" field will not
      be set.
    """
    if not token:
        return None
    if ':' not in token:
        logging.warn('Malformed token: no signature separator')
        return None
    sig, body = token.split(':', 1)
    if _DISABLE_CRYPTO:
        plaintext = body
    else:
        key_storage = KeyStorage.get()
        hmac_key = key_storage.hmac_key
        if type(hmac_key) == unicode:
            # Crypto requires byte strings
            hmac_key = hmac_key.encode('utf8')
        computed_sig = HMAC.HMAC(key=hmac_key,
                                 msg=body).hexdigest()
        if sig != computed_sig:
            logging.warn('Malformed token: invalid signature')
            return None
        try:
            plaintext = AES.new(key_storage.aes_key,
                                AES.MODE_CBC).decrypt(body)
        except ValueError:
            logging.warn('Malformed token: wrong size')
            return None
    # Remove excess whitespace.
    plaintext = plaintext.strip()
    # The plaintext should contain at least one space.
    if ' ' not in plaintext:
        logging.warn('Malformed token: bad contents')
        return None
    parts = plaintext.split(' ')
    if len(parts) != 2:
        logging.warn('Malformed token: bad structure')
        return None
    timestamp, email = parts
    try:
        timestamp = int(timestamp, 16)
    except ValueError:
        logging.warn('Malformed token: bad timestamp')
        return None
    # Reject tokens that are too old or which have time-traveled.  We
    # allow for 1s of clock skew.
    age_s = time.time() - timestamp
    if age_s < -1 or age_s > _TOKEN_TIMEOUT_S:
        logging.warn('Malformed token: expired (age=%ds)', age_s)
        return None
    cred = _Credentials()
    cred.email = email
    cred.security_token_is_stale = (age_s > 0.5 * _TOKEN_TIMEOUT_S)
    return cred


def attach_credentials(response, user):
    """Attach a user's credentials to a response.

    Args:
      response: An HttpResponse object.
      user: A User object.
    """
    response.set_cookie(_CHIRP_SECURITY_TOKEN_COOKIE,
                        _create_security_token(user))


def get_current_user(request):
    """Get the current logged-in user's.

    Returns:
      A User object, or None if the user is not logged in.

    Raises:
      UserNotAllowedError if the user is prohibited from accessing
        the site.
    """
    cred = None
    token = request.COOKIES.get(_CHIRP_SECURITY_TOKEN_COOKIE)
    if token:
        cred = _parse_security_token(token)
    # If this is a POST, look for a base64-encoded security token in
    # the CHIRP_Auth variable.
    if cred is None and request.method == 'POST':
        token = request.POST.get("CHIRP_Auth")
        if token:
            try:
                token = base64.urlsafe_b64decode(token)
            except TypeError:
                token = None
            if token:
                cred = _parse_security_token(token)
    # No valid token?  This is hopeless!
    if cred is None:
        return None
    # Try to find a user for this email address.
    user = User.get_by_email(cred.email)
    if user is None:
        return None
    # Reject inactive users.
    if not user.is_active:
        logging.info('Rejected inactive user %s', user.email)
        raise UserNotAllowedError
    user._credentials = cred
    return user


def create_login_url(path):
    """Returns the URL of a login page that redirects to 'path' on success."""
    return "/auth/hello?redirect=%s" % path


def logout(redirect=None):
    """Create an HTTP response that will log a user out.
    
    The redirect param can be a relative URL in which case 
    the user will go back to the same page when logging in.
    This is useful for switching users like on the playlist 
    tracker page.
    
    Returns:
      An HttpResponse object that will log the user out.
    """
    # If the user was signed in and has a cookie, clear it.
    logout_url = _FINAL_LOGOUT_URL
    if redirect:
        logout_url = '%s?redirect=%s' % (logout_url, redirect)
    response = http.HttpResponseRedirect(logout_url)
    response.set_cookie(_CHIRP_SECURITY_TOKEN_COOKIE, '')
    return response


def get_password_reset_token(user):
    """A URL-safe token that authenticates a user for a password reset."""
    return base64.urlsafe_b64encode(_create_security_token(user))


def parse_password_reset_token(token):
    """Extracts an email address from a valid password reset token."""
    try:
        token = base64.urlsafe_b64decode(str(token))
    except TypeError:
        return None
    cred = _parse_security_token(token)
    return cred and cred.email
