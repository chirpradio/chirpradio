
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

import calendar
from datetime import datetime, timedelta
import hashlib
import logging
import time

import webapp2 as webapp
from google.appengine.api import memcache, taskqueue
try:
    import json as simplejson
except ImportError:
    import simplejson

from playlists.models import (chirp_playlist_key, PlaylistTrack,
                              PlayCountSnapshot)
from playlists.tasks import _push_notify
from djdb import pylast
from common import dbconfig


log = logging.getLogger()


class ApiHandler(webapp.RequestHandler):
    use_cache = False
    memcache_ttl = 60  # seconds

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
                memcache.set(self.cache_key, data, time=self.memcache_ttl)
        self.check_data(data)
        # Default encoding is UTF-8
        js = simplejson.dumps(data)
        if self.request.str_GET.get('jsonp'):
            self.response.headers['Content-Type'] = 'application/x-javascript'
            js = '%s(%s);' % (self.request.str_GET['jsonp'], js)

        # Clients shouldn't poll more than 15 seconds but we want to make
        # sure they don't miss new tracks so the cache here is low.
        # Note that this cache time is just for clients, it does not affect
        # memcache.
        cache_for_secs = 10
        expires = ((datetime.utcnow() + timedelta(seconds=cache_for_secs))
                   .strftime("%a, %d %b %Y %H:%M:%S +0000"))
        self.response.headers['Expires'] = expires
        self.response.headers['Cache-Control'] = \
                                'public, max-age=%s' % cache_for_secs

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
                                  queue_name='lastfm',
                                  params={'id': track['id']})
                except:
                    log.exception('IGNORED while adding task')

    def track_as_data(self, track):
        # Create Unix timestamps.
        played_g = track.established.utctimetuple()
        played_local = time.mktime(track.established_display.timetuple())
        played_local_expire = (track.established_display +
                               timedelta(days=6 * 31))
        return {
            'id': str(track.key()),
            'artist': track.artist_name,
            'artist_is_local': bool(any(ct in track.categories
                                        for ct in ('local_current',
                                                   'local_classic'))),
            'track': track.track_title,
            'release': track.album_title,
            'label': track.label_display,
            'notes': track.notes or '',
            'dj': track.selector.effective_dj_name,
            'played_at_gmt': track.established.isoformat(),
            'played_at_gmt_ts': calendar.timegm(played_g),
            'played_at_local': track.established_display.isoformat(),
            'played_at_local_expire': played_local_expire.isoformat(),
            'played_at_local_ts': played_local,
            'lastfm_urls': {
                'sm_image': track.lastfm_url_sm_image,
                'med_image': track.lastfm_url_med_image,
                'large_image': track.lastfm_url_large_image,
                '_processed': track.lastfm_urls_processed,
            }
        }

    def get_json(self):
        playlist_key = chirp_playlist_key()
        recent_tracks = list(PlaylistTrack.all()
                                .filter('playlist =', playlist_key)
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
        _push_notify('chirpradio.push.update-playlist-storage')
        self.response.out.write(simplejson.dumps({
            'success': True,
            'links_fetched': links_fetched
        }))


class Stats(CachedApiHandler):
    """CHIRP Radio statistics for weekly plays, etc."""
    cache_key = 'api.stats'
    memcache_ttl = 60 * 60 * 4  # 4 hours

    def get_json(self):
        end = datetime.now()
        start = end - timedelta(days=7)
        qs = (PlayCountSnapshot.all()
              .filter('established >=', start)
              .filter('established <=', end))

        # Collect the play counts.
        weekly = {}
        for count in qs.run():
            id = count.track_id
            weekly.setdefault(id, {'play_count': []})
            weekly[id].update({'artist': count.artist_name,
                               'release': count.album_title,
                               'label': count.label,
                               'id': id})
            weekly[id]['play_count'].append(count.play_count)

        for key, stat in weekly.iteritems():
            pc = stat['play_count']
            weekly[key].update({
                # Average the play counts per release.
                'play_count': int(round(sum(pc) / len(pc), 1)),
                # Make this ID shorter so it's easier for clients.
                'id': hashlib.sha1(stat['id']).hexdigest()
            })

        # Sort the releases in descending order of play count.
        rel = sorted(weekly.values(),
                     key=lambda c: (c['play_count'], c['release']),
                     reverse=True)
        # Limit to top 40.
        rel = rel[0:40]

        return {
            'this_week': {
                'start': start.strftime('%Y-%m-%d'),
                'end': end.strftime('%Y-%m-%d'),
                'releases': rel
            }
        }


services = [('/api/', Index),
            ('/api/current_playlist', CurrentPlaylist),
            ('/api/stats', Stats),
            ('/api/_check_lastfm_links', CheckLastFMLinks)]
debug = False

application = webapp.WSGIApplication(services, debug=debug)
