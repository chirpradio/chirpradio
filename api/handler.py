
###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the 'License');
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an 'AS IS' BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

# Installs app engine django even though the API doesn't need it.
# This is currently a workaround to prevent Django 0.96 polluting the
# process space that each server instance is running in.
# See http://code.google.com/p/google-app-engine-django/issues/detail?id=191
import main


import logging

from google.appengine.ext import webapp
from google.appengine.api import memcache, taskqueue
from google.appengine.ext.webapp.util import run_wsgi_app
import simplejson

from playlists.models import ChirpBroadcast, PlaylistTrack
from djdb import pylast
from common import dbconfig


log = logging.getLogger()


class ApiHandler(webapp.RequestHandler):
    use_cache = False

    def get(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Cache-Control'] = 'public, max-age=30'
        if not self.use_cache:
            data = self.get_json()
        else:
            if self.cache_key is None:
                raise NotImplementedError("cache_key was not set")
            data = memcache.get(self.cache_key)
            if not data:
                data = self.get_json()
                memcache.set(self.cache_key, data, time=60)
        self.check_data(data)
        # Default encoding is UTF-8
        js = simplejson.dumps(data)
        if self.request.str_GET.get('jsonp'):
            self.response.headers['Content-Type'] = 'application/x-javascript'
            js = '%s(%s);' % (self.request.str_GET['jsonp'], js)
        self.response.out.write(js)

    def check_data(self, data):
        """Optional hook to do something with the view's data.

        This hook will be called even if the data was cached
        so be careful not to use expensive resources.
        """


class CachedApiHandler(ApiHandler):
    use_cache = True
    cache_key = None


def iter_tracks(data):
    yield data['now_playing']
    for track in data['recently_played']:
        yield track


class CurrentPlaylist(CachedApiHandler):
    """Current track playing on CHIRP and recently played tracks."""
    cache_key = 'api.current_track'

    def check_data(self, data):
        for track in iter_tracks(data):
            if not track['lastfm_urls']['_processed']:
                try:
                    taskqueue.add(url='/api/_check_lastfm_links',
                                  params={'id': track['id']})
                except:
                    log.exception('IGNORED while adding task')

    def track_as_data(self, track):
        return {
            'id': str(track.key()),
            'artist': track.artist_name,
            'track': track.track_title,
            'release': track.album_title,
            'label': track.label_display,
            'dj': track.selector.effective_dj_name,
            'played_at_gmt': track.established.isoformat(),
            'played_at_local': track.established_display.isoformat(),
            'lastfm_urls': {
                'sm_image': track.lastfm_url_sm_image,
                'med_image': track.lastfm_url_med_image,
                'large_image': track.lastfm_url_large_image,
                '_processed': track.lastfm_urls_processed,
            }
        }

    def get_json(self):
        broadcast = ChirpBroadcast()
        recent_tracks = list(PlaylistTrack.all()
                                .filter('playlist =', broadcast)
                                .order('-established')
                                .fetch(6))
        return {
            'now_playing': self.track_as_data(recent_tracks.pop(0)),
            # Last 5 played tracks:
            'recently_played': [self.track_as_data(t) for t in recent_tracks]
        }

    def post(self):
        # For some reason _ah/warmup is posting to current_playlist
        # instead of GET.  This might be a bug or it might be some 'ghost
        # tasks' stuck in the queue.
        log.warning("Unexpected POST request")
        return self.get()


class Index(ApiHandler):
    """Lists available resources."""

    def get_json(self):
        return {
            'services': [(url, s.__doc__)
                         for url, s in services if issubclass(s, ApiHandler)]
        }


class CheckLastFMLinks(webapp.RequestHandler):

    def post(self):
        links_fetched = 0
        if not self.request.POST.get('id'):
            # This is a temporary workaround to free up the task queue. It
            # seems that old tasks are stuck in an error-retry loop
            log.error('id not found in POST')
            self.response.out.write(simplejson.dumps({'success': False}))
            return
        track = PlaylistTrack.get(self.request.POST['id'])
        if track is None:
            # Track was deleted by DJ, other scenarios?
            log.warning('track does not exist: %s' % self.request.POST['id'])
            self.response.out.write(simplejson.dumps({'success': False}))
            return
        try:
            fm = pylast.get_lastfm_network(
                                api_key=dbconfig['lastfm.api_key'])
            fm_album = fm.get_album(track.artist_name, track.album_title)
            track.lastfm_url_sm_image = \
                            fm_album.get_cover_image(pylast.COVER_SMALL)
            track.lastfm_url_med_image = \
                            fm_album.get_cover_image(pylast.COVER_MEDIUM)
            track.lastfm_url_large_image = \
                            fm_album.get_cover_image(pylast.COVER_LARGE)
        except pylast.WSError:
            # Probably album not found
            log.exception('IGNORED while fetching LastFM data')
        track.lastfm_urls_processed = True  # Even on error
        track.save()
        memcache.delete(CurrentPlaylist.cache_key)
        self.response.out.write(simplejson.dumps({
            'success': True,
            'links_fetched': links_fetched
        }))


services = [('/api/', Index),
            ('/api/current_playlist', CurrentPlaylist),
            ('/api/_check_lastfm_links', CheckLastFMLinks)]
debug = False
application = webapp.WSGIApplication(services, debug=debug)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
