
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
            reponse = self._get_json_response()
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


class CurrentTrack(CachedApiHandler):
    """Current track playing on CHIRP."""
    cache_key = 'api.current_track'

    def get_json(self):
        broadcast = ChirpBroadcast()
        current_track = (PlaylistTrack.all()
                            .filter('playlist =', broadcast)
                            .order('-established'))[0]
        return {
            'artist': current_track.artist_name,
            'track': current_track.track_title,
            'release': current_track.album_title,
            'label': current_track.label_display,
            'dj': current_track.selector.dj_name,
            'played_at_gmt': current_track.established.isoformat(),
            'played_at_local': current_track.established_display.isoformat()
        }


class Index(ApiHandler):
    """Lists available resources."""

    def get(self):
        self.json_response({
            'services': [(url, s.__doc__) for url, s in services]
        })


services = [('/api/', Index),
            ('/api/current_track', CurrentTrack)]
debug = False
application = webapp.WSGIApplication(services, debug=debug)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
