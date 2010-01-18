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

"""Views for DJ Playlists."""
import logging
from datetime import datetime, timedelta

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import loader, RequestContext

from google.appengine.api.datastore_errors import BadKeyError

from auth.decorators import require_role
import auth
from auth import roles
from playlists.forms import PlaylistTrackForm, PlaylistReportForm
from playlists.models import PlaylistTrack, PlaylistEvent, PlaylistBreak, ChirpBroadcast
from playlists.tasks import playlist_event_listeners
from common.utilities import as_encoded_str


common_context = {
    'title': 'CHIRPradio.org DJ Playlist Tracker'
}

class PlaylistEventView(object):
    """UI wrapper around playlist event data object
    with extra attributes for use in templates.

    Extra attributes available on view objects:

    **is_break**
    True if this event is a song break

    **is_new**
    True if this event is a song played before the last break.
    Note that this attribute is controlled by iter_playlist_events_for_view()

    """

    def __init__(self, playlist_event):
        self.playlist_event = playlist_event
        self.is_break = type(self.playlist_event) is PlaylistBreak
        self.is_new = False

    def __getattr__(self, key):
        return getattr(self.playlist_event, key)

def iter_playlist_events_for_view(query):
    """Iterate a query of playlist event objects.

    returns a generator to produce PlaylistEventView() objects
    which contain some extra attributes for the view.
    """
    first_break = False
    for playlist_event in query:
        pl_view = PlaylistEventView(playlist_event)
        if pl_view.is_break:
            first_break = True
        if not first_break:
            pl_view.is_new = True
        yield pl_view



def get_vars(request):
    current_user = auth.get_current_user(request)

    if request.method == 'POST':
        form = PlaylistTrackForm(data=request.POST)
    else:
        form = PlaylistTrackForm()
    form.current_user = current_user
    form.playlist = ChirpBroadcast()

    vars = {
        'form': form,
        'playlist': form.playlist
    }
    vars.update(common_context)
    return vars


def get_playlist_history(playlist):
    pl = PlaylistEvent.all().filter('playlist =', playlist)
    pl = pl.filter('established >=', datetime.now() - timedelta(hours=3))
    pl = pl.order('-established')
    return list(iter_playlist_events_for_view(pl))

@require_role(roles.DJ)
def landing_page(request):
    vars = get_vars(request)

    # load the playlist history
    vars['playlist_events'] = get_playlist_history(vars['playlist'])

    return render_to_response('playlists/landing_page.html', vars,
            context_instance=RequestContext(request))


@require_role(roles.DJ)
def create_event(request):
    vars = get_vars(request)

    if request.method == 'POST':

        # special case...
        if request.POST.get('submit') == 'Add Break':
            b = PlaylistBreak(playlist=vars['playlist'])
            b.put()
            vars['add_break'] = True
            # errors should not display on add break, reset internal hash
            vars['form']._errors = {}

        elif vars['form'].is_valid():
            track = vars['form'].save()
            playlist_event_listeners.create(track)
            return HttpResponseRedirect(reverse('playlists_landing_page'))

    vars['playlist_events'] = get_playlist_history(vars['playlist'])

    return render_to_response('playlists/landing_page.html', vars,
            context_instance=RequestContext(request))


@require_role(roles.DJ)
def delete_event(request, event_key):
    e = None
    try:
        e = PlaylistEvent.get(event_key)
    except BadKeyError:
        pass
    else:
        if e and e.selector.key() == auth.get_current_user(request).key():
            e.delete()
            playlist_event_listeners.delete(event_key)

    return HttpResponseRedirect(reverse('playlists_landing_page'))



@require_role(roles.MUSIC_DIRECTOR)
def report_playlist(request):
    vars = {}

    # report vars
    items = None
    fields = ['from_date', 'to_date', 'album_title', 'artist_name', 'label', 'play_count']

    # default report
    if request.method == 'GET':
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=7)
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

def http_send_csv_file(fname, fields, items):
    import csv

    # dump item using key fields
    def item2row(i):
        return [as_encoded_str(i[key], encoding='utf8') for key in fields]

    # use response obj to set filename of downloaded file
    response = HttpResponse(mimetype='text/csv')
    # TODO(Kumar) mark encoding as UTF-8?
    response['Content-Disposition'] = "attachment; filename=%s.csv" % (fname)

    # write data out
    out = csv.writer(response)
    out.writerow(fields)
    for item in items:
        out.writerow(item2row(item))
    #
    return response

# TODO: move following funcs to models
def filter_tracks_by_date_range(from_date, to_date):
    playlist = ChirpBroadcast()
    pl = PlaylistTrack.all().filter('playlist =', playlist)
    pl = pl.filter('established >=', from_date)
    pl = pl.filter('established <=', to_date)
    pl = pl.order('-established')
    return pl

def query_group_by_track_key(from_date, to_date):
    ''' app engine Query and GqlQuery do not support SQL group by
    manually count each record and group them by some unique key
    '''

    query = filter_tracks_by_date_range(from_date, to_date)
    fields = ['album_title', 'artist_name', 'label']

    #
    key_item = 'group_by_key'
    key_counter = 'play_count'

    # group by key/fields
    def item_key(item):
        key_parts = []
        for key in fields:
            stub = as_encoded_str(getattr(item, key, ''))
            if stub is None:
                # for existing None-type attributes
                stub = ''
            stub = stub.lower()
            key_parts.append(stub)
        return ','.join(key_parts)

    # dict version of db rec
    def item2hash(item):
        d = {}
        for key in fields:
            d[key] = getattr(item, key, None)

        # init additional props
        d[key_counter] = 0
        d['from_date'] = from_date
        d['to_date'] = to_date

        return d

    # unique list of tracks with order
    items = []

    # hash of seen keys
    seen = {}

    #
    for item in query:
        key = item_key(item)

        if not seen.has_key(key):
            x = item2hash(item)
            seen[key] = x
            items.append(x)

        # inc counter
        seen[key][key_counter] += 1

    return items

