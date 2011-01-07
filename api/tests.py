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

    def tearDown(self):
        assert memcache.flush_all()


class TestCurrentTrack(APITest):

    def setUp(self):
        super(TestCurrentTrack, self).setUp()

        (self.stevie,
         self.talking_book,
         self.tracks) = create_stevie_wonder_album_data()

        self.dj = User(dj_name='DJ Night Moves', first_name='Steve',
                       last_name='Dolfin', email='steve@dolfin.org',
                       roles=[auth.roles.DJ])
        self.dj.save()
        self.playlist = ChirpBroadcast()
        self.playlist_track = PlaylistTrack(
                playlist=self.playlist,
                selector=self.dj,
                artist=self.stevie,
                album=self.talking_book,
                track=self.tracks['You Are The Sunshine Of My Life'],
                freeform_label='Motown')
        self.playlist_track.save()

    def tearDown(self):
        super(TestCurrentTrack, self).tearDown()
        clear_data()

    def test_data_fields(self):
        r = self.client.get('/api/current_track')
        eq_(r.status, '200 OK')
        eq_(r.headers['content-type'], 'application/json')
        data = simplejson.loads(r.body)
        eq_(data['artist'], 'Stevie Wonder')
        eq_(data['track'], 'You Are The Sunshine Of My Life')
        eq_(data['release'], 'Talking Book')
        eq_(data['dj'], 'DJ Night Moves')
        eq_(data['played_at_gmt'].split('T')[0],
            self.playlist_track.established.strftime('%Y-%m-%d'))
        eq_(data['played_at_local'].split('T')[0],
            self.playlist_track.established_display.strftime('%Y-%m-%d'))

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
        r = self.client.get('/api/current_track')
        eq_(r.status, '200 OK')
        data = simplejson.loads(r.body)
        eq_(data['artist'], unicode_text)
        eq_(data['track'], unicode_text)
        eq_(data['release'], unicode_text)
        eq_(data['dj'], unicode_text)

    def test_cache_flushing(self):
        r = self.client.get('/api/current_track')
        eq_(r.status, '200 OK')
        data = simplejson.loads(r.body)
        eq_(data['track'], 'You Are The Sunshine Of My Life')

        # Play another track:
        self.playlist_track = PlaylistTrack(
                playlist=self.playlist,
                selector=self.dj,
                artist=self.stevie,
                album=self.talking_book,
                track=self.tracks['You And I (We Can Conquer The World)'],
                freeform_label='Motown')
        self.playlist_track.save()

        r = self.client.get('/api/current_track')
        eq_(r.status, '200 OK')
        data = simplejson.loads(r.body)
        eq_(data['track'], 'You And I (We Can Conquer The World)')
