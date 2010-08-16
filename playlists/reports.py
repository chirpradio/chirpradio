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

import datetime
from datetime import timedelta

from django.template import loader, RequestContext

from auth.decorators import require_role
import auth
from auth import roles
from common.utilities import as_encoded_str, http_send_csv_file
from playlists.forms import PlaylistTrackForm, PlaylistReportForm
from playlists.views import query_group_by_track_key
from playlists.models import PlaylistTrack, PlaylistEvent, PlaylistBreak, ChirpBroadcast

@require_role(roles.MUSIC_DIRECTOR)
def report_playlist(request):
    vars = {}

    # report vars
    items = None
    fields = ['from_date', 'to_date', 'album_title', 'artist_name', 'label', 'play_count']

    # default report
    if request.method == 'GET':
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=1)
        items = query_group_by_track_key(from_date, to_date)

        # default form
        form = PlaylistReportForm({'from_date':from_date, 'to_date':to_date})

    # check form data post
    elif request.method == 'POST':

        # generic search form
        form = PlaylistReportForm(data=request.POST)
        if form.is_valid():
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']


            # special case to download report
            if request.POST.get('download') == 'Download':
                fname = "chirp-play-count_%s_%s" % (from_date, to_date)
                return http_send_csv_file(fname, fields, query_group_by_track_key(from_date, to_date))

            # generate report from date range
            if request.POST.get('search') == 'Search':
                items = query_group_by_track_key(from_date, to_date)

    # template vars
    vars['form'] = form

    if items:
        vars['fields'] = fields
        vars['tracks'] = query_group_by_track_key(from_date, to_date)

    return render_to_response('playlists/reports.html', vars,
            context_instance=RequestContext(request))
