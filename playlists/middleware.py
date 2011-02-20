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
    """Manage the request.is_from_studio based on IP address and POST override variables.   People should only submit new items to the playlist if they are in the studio.  This is managed by a list of IP addresses in the Config entity.  If someone is not in the studio they are presented with a warning and override checkbox. The playlist view should only process a request if request.is_in_studio is True."""

    DB_KEY = 'chirp.studio_ip_range'
    COOKIE_NAME = 'is_from_studio'

    def __init__(self):
        self.is_from_studio = False
        self.set_cookie = False
        
    def process_request(self, request):

        studio_ip_range = []
        current_user_ip = request.META.get('REMOTE_ADDR', '')
        post_val_override = request.POST.get('is_from_studio_override', False)

        if request.COOKIES.get(self.COOKIE_NAME, 'False') == 'True':
            self.is_from_studio = True
            log.info('Found %s cookie.' % self.COOKIE_NAME)
        else:
            try:
                # chirp_studio_ip_range is comma delimited string
                studio_ip_range = dbconfig[self.DB_KEY].split(',')
            except KeyError:
                log.error("Could not find key '%s' in dbconfig." % self.DB_KEY)
                pass
            else:
                if current_user_ip and current_user_ip in studio_ip_range:
                    self.set_cookie = True
                    self.is_from_studio = True

        # check override in POST
        if not self.is_from_studio and post_val_override:
            self.set_cookie = True
            log.warning("This person %s %s is overriding the studio ip range %s." % (
                request.user, current_user_ip, studio_ip_range))

        request.is_from_studio = self.is_from_studio
        log.warning("request.is_from_studio is %s." % request.is_from_studio)

    def process_response(self, request, response):
        if self.set_cookie:
            log.info('Setting %s cookie.' % self.COOKIE_NAME)
            response.cookies[self.COOKIE_NAME] = self.is_from_studio
            #response.cookies.add_header(
            #    'Set-Cookie',
            #    'is_from_studio=%s; expires=Fri, 31-Dec-2020 23:59:59 GMT' % \
            #    self.is_from_studio)
        return response

