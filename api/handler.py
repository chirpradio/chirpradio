
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

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson

from playlists.models import ChirpBroadcast, PlaylistTrack


class ApiHandler(webapp.RequestHandler):
    use_cache = False

    def get(self):
        self.response.headers['Content-Type'] = 'application/json'
        if not self.use_cache:
            response = self._get_json_response()
        else:
            if self.cache_key is None:
                raise NotImplementedError("cache_key was not set")
            response = memcache.get(self.cache_key)
            if not response:
                response = self._get_json_response()
                memcache.set(self.cache_key, response)
        self.response.out.write(response)

    def _get_json_response(self):
        data = self.get_json()
        # Default encoding is UTF-8
        return simplejson.dumps(data)


class CachedApiHandler(ApiHandler):
    use_cache = True
    cache_key = None


class CurrentPlaylist(CachedApiHandler):
    """Current track playing on CHIRP and recently played tracks."""
    cache_key = 'api.current_track'

    def track_as_data(self, track):
        return {
            'id': str(track.key()),
            'artist': track.artist_name,
            'track': track.track_title,
            'release': track.album_title,
            'label': track.label_display,
            'dj': track.selector.effective_dj_name,
            'played_at_gmt': track.established.isoformat(),
            'played_at_local': track.established_display.isoformat()
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
            'services': [(url, s.__doc__) for url, s in services]
        }


services = [('/api/', Index),
            ('/api/current_playlist', CurrentPlaylist)]
debug = False
application = webapp.WSGIApplication(services, debug=debug)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
