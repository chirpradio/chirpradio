# -*- coding: utf8 -*-
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

from __future__ import with_statement
import urllib
import unittest

from django.utils import simplejson
import fudge
from google.appengine.api import memcache
from google.appengine.api.taskqueue import TransientError
from nose.tools import eq_
from webtest import TestApp

import api.handler
from api.handler import iter_tracks
from api.handler import application
import auth.roles
from auth.models import User
from playlists.models import Playlist, PlaylistTrack, ChirpBroadcast
from playlists.tests.test_views import create_stevie_wonder_album_data
from common import dbconfig
from djdb import pylast


def clear_data():
    for pl in Playlist.all():
        for track in PlaylistTrack.all().filter('playlist =', pl):
            track.delete()
        pl.delete()
    for u in User.all():
        u.delete()


class APITest(unittest.TestCase):

    def setUp(self):
        dbconfig['lastfm.api_key'] = 'SEKRET_LASTFM_KEY'
        self.client = TestApp(application)
        self.dj = User(dj_name='DJ Night Moves', first_name='Steve',
                       last_name='Dolfin', email='steve@dolfin.org',
                       roles=[auth.roles.DJ])
        self.dj.save()
        self.playlist = ChirpBroadcast()
        (self.stevie,
         self.talking_book,
         self.tracks) = create_stevie_wonder_album_data()

    def tearDown(self):
        assert memcache.flush_all()
        clear_data()

    def play_stevie_song(self, song_name):
        self.playlist_track = PlaylistTrack(
                playlist=self.playlist,
                selector=self.dj,
                artist=self.stevie,
                album=self.talking_book,
                track=self.tracks[song_name],
                freeform_label='Motown')
        self.playlist_track.save()

    def request(self, url):
        r = self.client.get(url)
        eq_(r.status, '200 OK')
        eq_(r.headers['content-type'], 'application/json')
        data = simplejson.loads(r.body)
        return data


class TestServiceIndex(APITest):

    def test_index(self):
        eq_(sorted([s[0] for s in self.request('/api/')['services']]),
            ['/api/',
             '/api/current_playlist'])


class TestTrackPlayingNow(APITest):

    def setUp(self):
        super(TestTrackPlayingNow, self).setUp()
        self.play_stevie_song('You Are The Sunshine Of My Life')

    def tearDown(self):
        super(TestTrackPlayingNow, self).tearDown()

    def test_data_fields(self):
        data = self.request('/api/current_playlist')
        current = data['now_playing']
        eq_(current['artist'], 'Stevie Wonder')
        eq_(current['track'], 'You Are The Sunshine Of My Life')
        eq_(current['release'], 'Talking Book')
        eq_(current['dj'], 'DJ Night Moves')
        eq_(current['played_at_gmt'].split('T')[0],
            self.playlist_track.established.strftime('%Y-%m-%d'))
        eq_(current['played_at_local'].split('T')[0],
            self.playlist_track.established_display.strftime('%Y-%m-%d'))
        assert 'id' in current

    def test_allow_post(self):
        # support for _ah/warmup ?
        r = self.client.post('/api/current_playlist', {})
        eq_(r.status, '200 OK')
        data = simplejson.loads(r.body)
        current = data['now_playing']
        eq_(current['artist'], 'Stevie Wonder')

    @fudge.patch('api.handler.taskqueue')
    def test_build_lastfm_links(self, fake_tq):
        fake_tq.expects('add').with_args(url='/api/_check_lastfm_links')
        data = self.request('/api/current_playlist')
        current = data['now_playing']
        eq_(current['lastfm_urls'], {
            'sm_image': None,
            'med_image': None,
            'large_image': None,
            '_processed': False
        })

    @fudge.patch('api.handler.taskqueue.add',
                 'api.handler.log')
    def test_build_lastfm_links_logs_errors(self, fake_add, fake_log):
        fake_add.expects_call().raises(TransientError)
        fake_log.expects('exception')
        data = self.request('/api/current_playlist')

    @fudge.patch('api.handler.taskqueue')
    def test_build_partial_lastfm_links(self, fake_tq):
        (fake_tq.expects('add')
                .with_args(url='/api/_check_lastfm_links')
                .times_called(2))
        data = self.request('/api/current_playlist')
        data['now_playing']['lastfm_urls']['sm_image'] = 'http://.../'
        memcache.set('api.current_track', data)
        data = self.request('/api/current_playlist')

    def test_non_ascii(self):
        unicode_text = 'フォクすけといっしょ'.decode('utf8')
        self.playlist_track.artist.name = unicode_text
        self.playlist_track.artist.save()
        self.playlist_track.album.title = unicode_text
        self.playlist_track.album.save()
        self.playlist_track.track.title = unicode_text
        self.playlist_track.track.save()
        self.playlist_track.selector.dj_name = unicode_text
        self.playlist_track.selector.save()
        data = self.request('/api/current_playlist')
        current = data['now_playing']
        eq_(current['artist'], unicode_text)
        eq_(current['track'], unicode_text)
        eq_(current['release'], unicode_text)
        eq_(current['dj'], unicode_text)

    def test_cache_flushing(self):
        data = self.request('/api/current_playlist')['now_playing']
        eq_(data['track'], 'You Are The Sunshine Of My Life')

        self.play_stevie_song('You And I (We Can Conquer The World)')
        data = self.request('/api/current_playlist')['now_playing']
        eq_(data['track'], 'You And I (We Can Conquer The World)')

    def test_jsonp_function(self):
        r = self.client.get('/api/current_playlist?%s'
                            % urllib.urlencode({'jsonp': 'parseRequest'}))
        eq_(r.status, '200 OK')
        assert r.body.startswith('parseRequest({'), (
                                            'Unexpected: %r' % r.body)
        assert r.body.endswith('});'), ('Unexpected: %r' % r.body)
        eq_(r.headers['content-type'], 'application/x-javascript')

    def test_jsonp_obj(self):
        r = self.client.get('/api/current_playlist?%s'
                            % urllib.urlencode({'jsonp': 'obj.parseRequest'}))
        eq_(r.status, '200 OK')
        assert r.body.startswith('obj.parseRequest({'), (
                                            'Unexpected: %r' % r.body)

    def test_jsonp_dict(self):
        r = self.client.get('/api/current_playlist?%s'
                            % urllib.urlencode(
                                {'jsonp': 'obj["parseRequest"]'}))
        eq_(r.status, '200 OK')
        assert r.body.startswith('obj["parseRequest"]({'), (
                                            'Unexpected: %r' % r.body)

    def test_jsonp_unicode(self):
        r = self.client.get('/api/current_playlist?%s' % urllib.urlencode(
                            {'jsonp': u'ivan_kristi\u0107'.encode('utf8')}))
        eq_(r.status, '200 OK')
        body = r.body.decode('utf8')
        assert body.startswith(u'ivan_kristi\u0107({'), (
                                            'Unexpected: %r' % body)


class TestRecentlyPlayedTracks(APITest):

    def setUp(self):
        super(TestRecentlyPlayedTracks, self).setUp()
        self.play_stevie_song('Tuesday Heartbreak')
        self.play_stevie_song('Big Brother')
        self.play_stevie_song('You Are The Sunshine Of My Life')
        self.play_stevie_song('Tuesday Heartbreak')
        self.play_stevie_song("You've Got It Bad Girl")
        self.play_stevie_song('Superstition')
        self.play_stevie_song('Big Brother')
        self.play_stevie_song('Blame It On The Sun')

    def test_data_fields(self):
        data = self.request('/api/current_playlist')
        eq_(data['now_playing']['track'], 'Blame It On The Sun')
        eq_([d['track'] for d in data['recently_played']],
            ['Big Brother',
             'Superstition',
             "You've Got It Bad Girl",
             "Tuesday Heartbreak",
             'You Are The Sunshine Of My Life'])

    def test_cache_flushing(self):
        data = self.request('/api/current_playlist')
        eq_([d['track'] for d in data['recently_played']],
            ['Big Brother',
             'Superstition',
             "You've Got It Bad Girl",
             "Tuesday Heartbreak",
             'You Are The Sunshine Of My Life'])

        self.play_stevie_song("Lookin' For Another Pure Love")
        data = self.request('/api/current_playlist')
        eq_([d['track'] for d in data['recently_played']],
            ['Blame It On The Sun',
             'Big Brother',
             'Superstition',
             "You've Got It Bad Girl",
             "Tuesday Heartbreak"])


class TestCheckLastFMLinks(APITest):

    def setUp(self):
        super(TestCheckLastFMLinks, self).setUp()
        self.play_stevie_song('Tuesday Heartbreak')
        self.play_stevie_song('Big Brother')

    @fudge.patch('api.handler.pylast.get_lastfm_network')
    def test_build_links(self, fm_getter):
        data = self.request('/api/current_playlist')
        (fm_getter.expects_call()
                  .with_args(api_key=dbconfig['lastfm.api_key'])
                  .returns_fake()
                  .expects('get_album')
                  .with_args('Stevie Wonder',
                             'Talking Book')
                  .returns_fake()
                  .expects('get_cover_image')
                  # First album images:
                  .with_args(pylast.COVER_SMALL)
                  .returns('http://last.fm/sm1.jpg')
                  .next_call()
                  .with_args(pylast.COVER_MEDIUM)
                  .returns('http://last.fm/med1.jpg')
                  .next_call()
                  .with_args(pylast.COVER_LARGE)
                  .returns('http://last.fm/large1.jpg')
                  .next_call()
                  # Second album images:
                  .with_args(pylast.COVER_SMALL)
                  .returns('http://last.fm/sm2.jpg')
                  .next_call()
                  .with_args(pylast.COVER_MEDIUM)
                  .returns('http://last.fm/med2.jpg')
                  .next_call()
                  .with_args(pylast.COVER_LARGE)
                  .returns('http://last.fm/large2.jpg'))

        # Simulate check_data() because taskqueue is disabled or something?
        for track in iter_tracks(data):
            self.client.post('/api/_check_lastfm_links',
                             {'id': track['id']})

        data = self.request('/api/current_playlist')
        current = data['now_playing']
        eq_(current['lastfm_urls'], {
            'sm_image': 'http://last.fm/sm1.jpg',
            'med_image': 'http://last.fm/med1.jpg',
            'large_image': 'http://last.fm/large1.jpg',
            '_processed': True
        })
        eq_(data['recently_played'][0]['lastfm_urls'], {
            'sm_image': 'http://last.fm/sm2.jpg',
            'med_image': 'http://last.fm/med2.jpg',
            'large_image': 'http://last.fm/large2.jpg',
            '_processed': True
        })

    @fudge.patch('api.handler.pylast.get_lastfm_network',
                 'api.handler.taskqueue')
    def test_recover_from_errors(self, fm_getter, fake_tq):
        (fm_getter.expects_call()
                  .with_args(api_key=dbconfig['lastfm.api_key'])
                  .returns_fake()
                  .expects('get_album')
                  .raises(pylast.WSError('', '', 'Album not found')))
        fake_tq.expects('add').times_called(3)  # only once for all songs

        data = self.request('/api/current_playlist')
        self.client.post('/api/_check_lastfm_links',
                         {'id': data['now_playing']['id']})

        data = self.request('/api/current_playlist')
        current = data['now_playing']
        eq_(current['lastfm_urls'], {
            'sm_image': None,
            'med_image': None,
            'large_image': None,
            '_processed': True
        })

    def test_non_existant_playlist_track(self):
        key = str(self.playlist_track.key())
        self.playlist_track.delete()
        r = self.client.post('/api/_check_lastfm_links', {'id': key})
        data = simplejson.loads(r.body)
        eq_(data['success'], False)
