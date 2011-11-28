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

"""Custom context processor for CHIRP request templates."""

from django.conf import settings

import auth

from common import time_util

def base(request):
    # logout should always redirect to the current page to 
    # make it easier to switch users (like on the playlist tracker)
    logout_url = "%s?redirect=%s" % (auth.LOGOUT_URL, request.path)
    return {
        'user': hasattr(request, 'user') and request.user or None,
        'login_url': auth.create_login_url('/'),
        'logout_url': logout_url,
        'settings': settings,
        'MEDIA_URL': settings.MEDIA_URL,
        'chicago_now': time_util.chicago_now(),
        'request': request,
        }
