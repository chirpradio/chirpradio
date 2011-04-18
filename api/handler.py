
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
        if not self.use_cache:
            data = self.get_json()
        else:
            if self.cache_key is None:
                raise NotImplementedError("cache_key was not set")
            data = memcache.get(self.cache_key)
            if not data:
                data = self.get_json()
                # Rely on the cache but only for a minute because
                # of the way server instances are distributed.
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


def iter_lastfm_links(data):
    for track in iter_tracks(data):
        for k,v in data['now_playing']['lastfm_urls'].items():
            yield (k,v)


class CurrentPlaylist(CachedApiHandler):
    """Current track playing on CHIRP and recently played tracks."""
    cache_key = 'api.current_track'

    def check_data(self, data):
        if any((v is None) for k,v in iter_lastfm_links(data)):
            try:
                taskqueue.add(url='/api/_check_lastfm_links')
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
                'sm_image': None,
                'med_image': None
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
        data = memcache.get(CurrentPlaylist.cache_key)
        if data:
            try:
                fm = pylast.get_lastfm_network(
                                    api_key=dbconfig['lastfm.api_key'])
                for track in iter_tracks(data):
                    links_fetched += 1
                    fm_album = fm.get_album(track['artist'], track['release'])
                    track['lastfm_urls']['sm_image'] = \
                            fm_album.get_cover_image(pylast.COVER_SMALL)
                    track['lastfm_urls']['med_image'] = \
                            fm_album.get_cover_image(pylast.COVER_MEDIUM)
            except pylast.WSError:
                # Probably album not found
                log.exception('IGNORED while fetching LastFM data')
            memcache.set(CurrentPlaylist.cache_key, data)
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
