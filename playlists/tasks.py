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
from datetime import datetime, timedelta
import sys
import logging
import urllib, urllib2
import wsgiref.handlers

from django import http
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import taskqueue, urlfetch

from common import dbconfig, in_dev
from common.utilities import as_encoded_str, cronjob
from common.autoretry import AutoRetry
from djdb.models import Track
from playlists.models import PlaylistEvent, PlayCount, PlayCountSnapshot

log = logging.getLogger()


class PlaylistEventListener(object):
    """Listens to creations or deletions of playlist entries."""

    def create(self, track):
        """This instance of PlaylistEvent was created."""
        raise NotImplementedError

    def delete(self, track_key):
        """The key of this PlaylistEvent was deleted."""
        raise NotImplementedError


class LiveSiteListener(PlaylistEventListener):
    """Tells chirpradio.org that a new entry was added to the playlist."""

    def create(self, track):
        """This instance of PlaylistEvent was created."""
        taskqueue.add(url=reverse('playlists.send_track_to_live_site'),
                      queue_name='live-site-playlists',
                      params={'id':str(track.key())})

    def delete(self, track_key):
        """The key of this PlaylistEvent was deleted."""


class PlayCountListener(PlaylistEventListener):
    """Keep track of how many times a track was played."""

    def create(self, track):
        """This instance of PlaylistEvent was created."""
        taskqueue.add(url=reverse('playlists.play_count'),
                      params={'id': str(track.key())})

    def delete(self, track_key):
        """The key of this PlaylistEvent was deleted."""


class PlaylistEventDispatcher(object):

    def __init__(self, listeners):
        self.listeners = listeners

    def create(self, *args, **kw):
        for listener in self.listeners:
            listener.create(*args, **kw)

    def delete(self, *args, **kw):
        for listener in self.listeners:
            listener.delete(*args, **kw)


playlist_event_listeners = PlaylistEventDispatcher([
    LiveSiteListener(),
    PlayCountListener(),
])


def send_track_to_live_site(request):
    """View for task queue that tells chirpradio.org a new track was entered"""
    log.info('Pushing notifications for track %r' % request.POST['id'])
    success = [_push_notify('chirpradio.push.update-playlist-storage'),  # this calls a Google Cloud Function
                _push_notify('chirpradio.push.tweet-now-playing'),  # this calls a Google Cloud Function
                _push_notify('chirpradio.push.now-playing'),                
                _push_notify('chirpradio.push.recently-played')]
    if all(success):
        return HttpResponse("OK")
    else:
        return HttpResponse("One or more push notifications failed",
                            status=500)


def _push_notify(url_key):
    url = dbconfig.get(url_key)
    if not url:
        msg = 'No value in dbconfig for %r' % url_key
        if in_dev():
            log.warning(msg)
        else:
            raise ValueError(msg)

    # A task has 10 minutes to execute. This tells urlfetch to time out after 8
    # minutes.
    deadline = 60 * 8
    resp = urlfetch.fetch(url, deadline=deadline)
    log.info('Push response from %r: %s' % (url, resp.status_code))
    if resp.status_code != 200:
        log.error(resp.content)

    return resp.status_code == 200


def play_count(request):
    """View for keeping track of play counts"""
    track_key = request.POST['id']
    track = PlaylistEvent.get(track_key)
    artist_name = track.artist_name
    album = track.album
    if not album:
        # Try to find a compilation album based on track name.
        qs = Track.all().filter('title =', track.track_title)
        for candidate in qs.run():
            if (candidate.track_artist and
                candidate.album.title == track.album_title and
                candidate.track_artist.name == track.artist_name):
                album = candidate.album
                break
        if not album:
            log.info('No album for %s / %s / %s'
                     % (track.artist_name, track.track_title,
                        track.album_title))
    if album and album.is_compilation:
        artist_name = 'Various'

    count = PlayCount.query(artist_name, track.album_title)
    if not count:
        count = PlayCount.create_first(artist_name,
                                       track.album_title,
                                       track.label)

    @db.transactional
    def increment(key):
        ob = db.get(key)
        ob.play_count += 1
        ob.put()

    increment(count.key())

    # See also:
    # https://developers.google.com/appengine/articles/sharding_counters
    return HttpResponse("OK")


@cronjob
def expunge_play_count(request):
    """Cron view to expire old play counts."""
    # Delete tracks that have not been incremented in the last week.
    qs = PlayCount.all().filter('modified <',
                                datetime.now() - timedelta(days=7))
    num = 0
    for ob in qs.fetch(1000):
        ob.delete()
        num += 1
    log.info('Deleted %s old play count entries' % num)


@cronjob
def play_count_snapshot(request):
    """Cron view to create a play count snapshot (top 40)."""
    qs = PlayCount.all().order('-play_count')
    results = []
    for count in qs.fetch(40):
        results.append(PlayCountSnapshot.create_from_count(count))
    for res in results:
        res.get_result()  # wait for result
    log.info('Created play count snapshot')


class AnyRequest(urllib2.Request):

    def get_method(self):
        if hasattr(self, 'http_method'):
            return getattr(self, 'http_method')
        else:
            return urllib2.Request.get_method(self)


def _fetch_url(url=None, data=None, method='GET', headers=None):
    if headers is None:
        headers = {}

    try:
        # request
        req = AnyRequest(url, data, headers)
        req.http_method = method

        # response
        res = urllib2.urlopen(req)
        d = {'code': res.code, 'content': res.read(), 'success':True}
        log.info("URL success output: %s" % d)
        return d
    except AssertionError:
        # short of listing every possible urllib2 exception,
        # this is the best I can think of to get the test suite to work
        # (i.e. mock assertions) -Kumar
        raise
    except Exception, e:
        # raise
        etype, val, tb = sys.exc_info()
        log.error(e)
        if hasattr(e, 'read'):
            content = e.read()
        else:
            content = None
        log.info("URL error output: %s" % content)
        return {'success': False,
                'exception_type': etype.__name__,
                'exception': val,
                'content': content}


"""Thin wrapper for taskqueue actions mapped in playlists/urls.py
"""

def task_response(result):
    if not result['success']:
        return HttpResponse("Task was unsuccessful", status=500)
    else:
        return HttpResponse("OK")
