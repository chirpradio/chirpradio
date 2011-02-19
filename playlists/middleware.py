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

"""Middleware for CHIRP's playlists system."""

from django import http
from common.models import DBConfig
import logging

dbconfig = DBConfig()
log = logging.getLogger()

class FromStudioMiddleware(object):

    def process_request(self, request):
        """Manage the request.is_from_studio and request.is_from_studio_override attributes based on IP address and POST variables.   People should only submit new items to the playlist if they are in the studio.  This is managed by a list of IP addresses in the Config entity.  If someone is not in the studio they are presented with a warning and override checkbox. The playlist form should only process a request if request.is_in_studio or request.is_in_studio_override are True."""

        request.is_from_studio = False
        request.is_from_studio_override = False
        key_ip_range = 'chirp_studio_ip_range'
        studio_ip_range = []
        current_user_ip = request.META.get('REMOTE_ADDR', '')
        current_user = request.user
        sess_val = request.SESSION.get('is_from_studio', False)
        sess_val_override = request.SESSION.get('is_from_studio_override', False)
        post_val_override = request.POST.get('is_from_studio_override', False)

        # process is_from_studio attr if not in the session
        if sess_val:
            request.is_from_studio = True
        else:
            try:
                # chirp_studio_ip_range is comma delimited string
                studio_ip_range = dbconfig[key_ip_range].split(',')
            except KeyError:
                log.error("Could not find key '%s' in dbconfig." % key_ip_range)
                pass
            else:
                if current_user_ip in studio_ip_range:
                    request.is_from_studio = True

        # check override in POST
        if not request.is_from_studio and not sess_val_override:
             if post_val_override:
                request.SESSION['is_from_studio_override'] = True
                log.warning("This person %s %s is overriding the studio ip range %s." % (
                    current_user, current_user_ip, studio_ip_range))

        # Might be good to only allow session var to be set if privs are right.
        #user = auth.get_current_user(request)
        #except auth.UserNotAllowedError:
        #    return http.HttpResponseForbidden('Access Denied!')
