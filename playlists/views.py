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

from google.appengine.api.datastore_errors import BadKeyError

from auth.decorators import require_role
import auth
from auth import roles
from playlists.forms import PlaylistTrackForm
from playlists.models import PlaylistTrack, PlaylistEvent, PlaylistBreak, ChirpBroadcast
from playlists.tasks import playlist_event_listeners


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
            playlist_event_listeners.create(track)
            return HttpResponseRedirect(reverse('playlists_landing_page'))

    return render_to_response('playlists/landing_page.html', vars)


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
