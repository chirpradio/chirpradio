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
from datetime import datetime, timedelta

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import loader, Context, RequestContext
from django.shortcuts import render_to_response, get_object_or_404

from google.appengine.api.datastore_errors import BadKeyError
from google.appengine.ext import deferred
from google.appengine.api.labs import taskqueue

from auth.decorators import require_role
import auth
from auth import roles
from playlists.forms import PlaylistTrackForm
from playlists.models import PlaylistTrack, PlaylistEvent, PlaylistBreak, ChirpBroadcast



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
        'current_user': current_user,
        'playlist': form.playlist
    }
    vars.update(common_context)
    return vars


@require_role(roles.DJ)
def landing_page(request):
    vars = get_vars(request)

    pl = PlaylistEvent.all().filter('playlist =', vars['playlist'])
    pl = pl.filter('established >=', datetime.now() - timedelta(hours=3))
    pl = pl.order('-established')

    vars['playlist_events'] = list(iter_playlist_events_for_view(pl))

    return render_to_response('playlists/landing_page.html', vars)


@require_role(roles.DJ)
def create_event(request):
    vars = get_vars(request)

    if request.method == 'POST':
        # special case...
        if request.POST.get('submit') == 'Add Break':
            b = PlaylistBreak(playlist=vars['playlist'])
            b.put()
            return HttpResponseRedirect(reverse('playlists_landing_page'))

        if vars['form'].is_valid():
            track = vars['form'].save()
            url_track_create(track)
            #taskqueue.add(url='/playlists/task_create', params={'id':str(track.key())})
            return HttpResponseRedirect(reverse('playlists_landing_page'))

    return render_to_response('playlists/landing_page.html', vars)


@require_role(roles.DJ)
def delete_event(request, event_key):
    try:
        e = PlaylistEvent.get(event_key)
        if e and e.selector.key() == auth.get_current_user(request).key():
            e.delete()
            url_track_delete(event_key)
            #taskqueue.add(url='/playlists/task_delete', params={'id':event_key})
    except BadKeyError:
        pass
    return HttpResponseRedirect(reverse('playlists_landing_page'))


"""
TODO(selizondo): get taskqueue/deferred task working

Publish Track being played to remote PHP server

URLs for PHP test server

    # status of last track published
    curl -v -X GET http://geoff.terrorware.com/hacks/chirpapi/playlist/current

    # create/publish track
    curl -v -X POST http://geoff.terrorware.com/hacks/chirpapi/playlist/create
         -d "track_name=s&track_label=l&track_artist=a&track_album=r&dj_name=d&time_played=2009-12-20 14:37&playlist_track_id=agpjaGlycHJhZGlvchMLEg1QbGF5bGlzdEV2ZW50GB0M"

    # delete previously published track using playlist_track_id from create
    curl -v -X DELETE http://geoff.terrorware.com/hacks/chirpapi/playlist/delete/website/agpjaGlycHJhZGlvchMLEg1QbGF5bGlzdEV2ZW50GB0M"
"""
import urllib
from google.appengine.api import urlfetch

def _urls(type='create'):
    urls = {
        #'create':'http://192.168.58.128:8101/api/track/',
        #'delete':'http://192.168.58.128:8101/api/track/'
        'create':'http://geoff.terrorware.com/hacks/chirpapi/playlist/create',
        'delete':'http://geoff.terrorware.com/hacks/chirpapi/playlist/delete/website/'
    }
    return urls[type]

"""Thin wrapper for taskqueue
"""
def task_create(request):
    try:
        track = PlaylistEvent.get(request.POST['id'])
        url_track_create(track)
    except:
        pass

def url_track_create(track=None):
    if track is None:
        return

    # TODO(selizondo): test against PHP URL
    url = _urls('create')
    form_data = urllib.urlencode({
        'track_name': track.track_title,
        'track_artist': track.artist_name,
        'track_album': track.album_title,
        'track_label': track.label,
        'dj_name': track.selector.last_name,
        'time_played': track.modified.strftime("%Y-%m-%d %H:%M:%S"),
        'playlist_track_id': str(track.key()),
    })

    #headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    result = urlfetch.fetch(url=url, payload=form_data, method=urlfetch.POST, headers=headers)
    #print result.status_code, result.content

"""Thin wrapper for taskqueue
"""
def task_delete(request):
    url_track_delete(request.POST['id'])

def url_track_delete(id):
    if not id:
        return

    # TODO(selizondo): test against PHP URL
    url = _urls('delete') + str(id)
    form_data = urllib.urlencode({'playlist_track_id': str(id)})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    result = urlfetch.fetch(url=url, payload=form_data, method=urlfetch.DELETE, headers=headers)
    #print result.status_code, result.content
