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

from google.appengine.api import datastore_errors, memcache
from google.appengine.api.datastore_errors import BadKeyError
from google.appengine.ext.db import Key

from auth.decorators import require_role
import auth
from auth import roles
from djdb.models import Album, HEAVY_ROTATION_TAG, LIGHT_ROTATION_TAG
from playlists.forms import PlaylistTrackForm
from playlists.models import (PlaylistTrack, PlaylistEvent, PlaylistBreak,
                              chirp_playlist_key, ChirpBroadcast)
from playlists.tasks import playlist_event_listeners
from common.utilities import as_encoded_str, http_send_csv_file
from common.autoretry import AutoRetry
from common import time_util
from common.time_util import chicago_now
from djdb.models import Track
from common.models import DBConfig

TRACKS_HEAVY_ROTATION_TARGET = 2
TRACKS_LIGHT_ROTATION_TARGET = 3
TRACKS_LOCAL_CURRENT_TARGET = 1
TRACKS_LOCAL_CLASSIC_TARGET = 1

dbconfig = DBConfig()
log = logging.getLogger()

common_context = {
    'title': 'CHIRPradio.org DJ Playlist Tracker',
    'page': 'playlists'
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


class CachedSelector(object):

    def __init__(self, key):
        self._key = key

    def key(self):
        return Key(encoded=self._key)


class CachedPlaylistEvent(object):

    def __init__(self, data):
        self._key = data['key']
        self.artist_name = data['artist_name']
        self.track_title = data['track_title']
        self.album_title_display = data['album_title_display']
        self.label_display = data['label_display']
        self.notes = data['notes']
        self.selector = CachedSelector(data['selector_key'])
        self.categories = data['categories']
        d = datetime(*data['established_display'])
        d = time_util.convert_utc_to_chicago(d)
        self.established_display = d

    def key(self):
        return Key(encoded=self._key)


def iter_playlist_events_for_view(query):
    """Iterate a query of playlist event objects.

    returns a generator to produce PlaylistEventView() objects
    which contain some extra attributes for the view.
    """
    first_break = False
    events = list(query)
    last_track = memcache.get('playlist.last_track')
    if last_track:
        # Prepend the last track from cache.
        # Due to HRD lag, this may not be in the result set yet.
        if not len(events) or last_track['key'] != str(events[0].key()):
            events.insert(0, CachedPlaylistEvent(last_track))
    for playlist_event in events:
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

    vars = {
        'form': form,
        'playlist': form.playlist
    }
    vars.update(common_context)
    return vars

def get_quotas(playlist):
    quotas = {'heavy_rotation_played': 0,
              'heavy_rotation_target': TRACKS_HEAVY_ROTATION_TARGET,
              'light_rotation_played': 0,
              'light_rotation_target': TRACKS_LIGHT_ROTATION_TARGET,
              'local_current_played': 0,
              'local_current_target': TRACKS_LOCAL_CURRENT_TARGET,
              'local_classic_played': 0,
              'local_classic_target': TRACKS_LOCAL_CLASSIC_TARGET}
    pl = PlaylistEvent.all().filter('playlist =', playlist)
    now = chicago_now()
    now.replace(second=0, microsecond=0)
    pl.filter('established >=', now - timedelta(seconds=60 * now.minute))
    pl.filter('established <', now + timedelta(seconds=60 * (60 - now.minute)))
    for event in iter_playlist_events_for_view(pl):
        if not event.is_break:
            if 'heavy_rotation' in event.categories:
                quotas['heavy_rotation_played'] += 1
            if 'light_rotation' in event.categories:
                quotas['light_rotation_played'] += 1
            if 'local_current' in event.categories:
                quotas['local_current_played'] += 1
            if 'local_classic' in event.categories:
                quotas['local_classic_played'] += 1

    return quotas

def get_playlist_history(playlist):
    pl = PlaylistEvent.all().filter('playlist =', playlist)
    pl = pl.filter('established >=', datetime.now() - timedelta(hours=3))
    pl = pl.order('-established')
    return list(iter_playlist_events_for_view(pl))

@require_role(roles.DJ)
def landing_page(request, vars=None):
    if vars is None:
        vars = get_vars(request)

    # Load quotas for tracks played.
    vars['quotas'] = get_quotas(vars['playlist'])
    now = chicago_now()
    vars['last_dt'] = datetime(now.year, now.month, now.day, now.hour)

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

    return landing_page(request, vars)

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
    playlist = chirp_playlist_key()
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
        if str(exc).startswith('ReferenceProperty failed to be resolved'):
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
            stub = as_encoded_str(_get_entity_attr(item, key, ''))

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
        d['heavy_rotation'] = int(bool(HEAVY_ROTATION_TAG in item.categories))
        d['light_rotation'] = int(bool(LIGHT_ROTATION_TAG in item.categories))

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
        if minutes > 0 and minutes % 25 == 0:
            pl_break = PlaylistBreak(
                           playlist=playlist,
                           established = datetime.now() - timedelta(minutes=minutes - 1))
            pl_break.put()
        minutes += 5

    return HttpResponseRedirect("/playlists/")


@require_role(roles.DJ)
def on_air(request):
    return render_to_response('playlists/on_air.html', {},
            context_instance=RequestContext(request))
