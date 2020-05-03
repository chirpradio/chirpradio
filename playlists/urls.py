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

urlpatterns = patterns('playlists',
    url(r'^create_event$', 'views.create_event', name="playlists_add_event"),
    url(r'^delete_event/([^/]+)$', 'views.delete_event', name="playlists_delete_event"),
    # TODO(Kumar) replace old URL with this when it's ready:
    url(r'^report/new$', 'reports.report_playlist_new', name="playlists_report_new"),
    url(r'^report$', 'reports.report_playlist', name="playlists_report"),
    url(r'^export_report$', 'reports.report_export_playlist', name="playlists_export_report"),
    url(r'^/?$', 'views.landing_page', name="playlists_landing_page"),
    url(r'^on-air/?$', 'views.on_air', name="playlists.on_air"),
    url(r'_bootstrap', 'views.bootstrap')
)

urlpatterns += patterns('playlists.tasks',
    url(r'^task/send_track_to_live_site$', 'send_track_to_live_site',
        name='playlists.send_track_to_live_site'),
    url(r'^task/play_count$', 'play_count',
        name='playlists.play_count'),
    url(r'^task/expunge_play_count$', 'expunge_play_count',
        name='playlists.expunge_play_count'),
    url(r'^task/play_count_snapshot$', 'play_count_snapshot',
        name='playlists.play_count_snapshot'),
)
