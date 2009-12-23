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

"""URLs for DJ Playlists."""

from django.conf import settings
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    '',
    url(r'^event$', 'playlists.views.add_event', name="playlists_add_event"),
    url(r'^event/([^/]+)/delete$', 'playlists.views.delete_event',
                                                name="playlists_delete_event"),
    url(r'^/?$', 'playlists.views.landing_page', name="playlists_landing_page"),
)
