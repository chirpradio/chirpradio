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
import unittest

from django.utils import simplejson
from google.appengine.api import memcache
from nose.tools import eq_
from webtest import TestApp

from api.handler import application
import auth.roles
from auth.models import User
from playlists.models import Playlist, PlaylistTrack, ChirpBroadcast
from playlists.tests.test_views import create_stevie_wonder_album_data


def clear_data():
    for pl in Playlist.all():
        for track in PlaylistTrack.all().filter('playlist =', pl):
            track.delete()
        pl.delete()
    for u in User.all():
        u.delete()


class APITest(unittest.TestCase):

    def setUp(self):
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