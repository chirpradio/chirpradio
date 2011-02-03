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

from google.appengine.api import datastore_errors
from google.appengine.api.datastore_errors import BadKeyError

from auth.decorators import require_role
import auth
from auth import roles
from playlists.forms import PlaylistTrackForm
from playlists.models import PlaylistTrack, PlaylistEvent, PlaylistBreak, ChirpBroadcast
from playlists.tasks import playlist_event_listeners
from common.utilities import as_encoded_str, http_send_csv_file
from common.autoretry import AutoRetry
from djdb.models import Track

log = logging.getLogger()

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
    for playlist_event in AutoRetry(query):
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
        e = AutoRetry(PlaylistEvent).get(event_key)
    except BadKeyError:
        pass
    else:
        if e and e.selector.key() == auth.get_current_user(request).key():
            e.delete()
            playlist_event_listeners.delete(event_key)

    return HttpResponseRedirect(reverse('playlists_landing_page'))

# TODO: move following funcs to models
def filter_tracks_by_date_range(from_date, to_date):
    fd = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0)
    td = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59)
    playlist = ChirpBroadcast()
    pl = PlaylistTrack.all().filter('playlist =', playlist)
    pl = pl.filter('established >=', fd)
    pl = pl.filter('established <=', td)
    pl = pl.order('-established')
    return pl

def _get_entity_attr(entity, attr, *getattr_args):
    """gets the value of an attribute on an entity.
    
    if the value is an orphaned reference then return 
    the string __bad_reference__ instead
    """
    try:
        if len(getattr_args):
            return getattr(entity, attr, *getattr_args)
        else:
            return getattr(entity, attr)
    except datastore_errors.Error, exc:
        if str(exc) == 'ReferenceProperty failed to be resolved':
            log.warning("Could not resolve reference property %r on %r at %s" % (
                                                            attr, entity, entity.key()))
            return '__bad_reference__'
        else:
            # something else happened
            raise

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
            try:
                stub = as_encoded_str(_get_entity_attr(item, key, ''))
            except datastore_errors.Error, exc:
                if str(exc) == 'ReferenceProperty failed to be resolved':
                    log.warning("Could not resolve reference property %r on %r at %r" % (
                                                                    key, item, item.key()))
                    stub = '__bad_reference__'
                else:
                    raise
                    
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
            d[key] = _get_entity_attr(item, key, None)

        # init additional props
        d[key_counter] = 0
        d['from_date'] = from_date
        d['to_date'] = to_date

        return d

    # unique list of tracks with order
    items = []

    # hash of seen keys
    seen = {}

    for item in AutoRetry(query):
        key = item_key(item)

        if not seen.has_key(key):
            x = item2hash(item)
            seen[key] = x
            items.append(x)

        # inc counter
        seen[key][key_counter] += 1

    return items

def bootstrap(request):
    # Don't create dummy playlist tracks if playlist tracks already exist!
    pl_tracks = PlaylistTrack.all().fetch(1)
    if len(pl_tracks) > 0:
        return HttpResponse(status=404)

    playlist = ChirpBroadcast()
    playlist.put()

    minutes = 0
    tracks = Track.all().fetch(100)
    for track in tracks:
        pl_track = PlaylistTrack(
                       playlist=playlist,
                       selector=request.user,
                       established = datetime.now() - timedelta(minutes=minutes),
                       artist=track.album.album_artist,
                       album=track.album,
                       track=track)
        pl_track.put()
        minutes += 5

    return HttpResponseRedirect("/playlists/")

