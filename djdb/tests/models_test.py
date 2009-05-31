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

import datetime
import unittest

from django import http
from django.test.client import Client

from google.appengine.ext import db

from djdb import models


class ModelsTestCase(unittest.TestCase):

    TEST_ARTIST_NAME = u'Test Artist'

    def setUp(self):
        # Create and save a test artist.
        self.test_artist = models.Artist(name=self.TEST_ARTIST_NAME)
        self.test_artist.save()

    def test_djdb_image(self):
        # Create and save a test image.
        img = models.DjDbImage(image_data="test data",
                               image_mimetype="image/jpeg",
                               sha1="test sha1")
        img.save()
        # Check the sha1 property.
        self.assertEqual("test sha1", img.sha1)
        # Check URL generation.
        expected_url = img.URL_PREFIX + img.sha1
        self.assertEqual(expected_url, img.url)
        # Check that images can be fetched by URL.
        by_url = models.DjDbImage.get_by_url(img.url)
        self.assertEqual(by_url.sha1, img.sha1)
        # Check that fetching by URL ignores leading text (such as a protocol
        # specification and hostname).
        by_url = models.DjDbImage.get_by_url("http://leading/junk/" + img.url)
        self.assertEqual(by_url.sha1, img.sha1)
        # Check that get_by_url returns None for a malformed URL.
        self.assertTrue(models.DjDbImage.get_by_url("/bad/url") is None)
        # Check that get_by_url returns None if we request a
        # non-existent image.
        no_sha1_url = models.DjDbImage.URL_PREFIX + "no such sha1"
        self.assertTrue(models.DjDbImage.get_by_url(no_sha1_url) is None)

    def test_artist(self):
        # Check that an artist object's unicode representation is the
        # name.
        self.assertEqual(self.TEST_ARTIST_NAME, unicode(self.test_artist))
    
    def test_album(self):
        # Check key generation against a known case.
        self.assertEqual(u'djdb/a:3039', models.Album.get_key_name(12345))

        # Tests of a single-artist album.
        alb = models.Album(title='test album',
                           album_id=12345,
                           import_timestamp=datetime.datetime.now(),
                           album_artist=self.test_artist,
                           num_tracks=13)
        # Check that the correct key is automatically assigned.
        self.assertEqual(models.Album.get_key_name(12345), alb.key().name())
        # Check the artist_name property.
        self.assertEqual(self.TEST_ARTIST_NAME, alb.artist_name)
        # Check that the album name is the unicode representation of
        # the object.
        self.assertEqual('test album', unicode(alb))

        # Tests of a compilation album.
        alb = models.Album(title='test album',
                           album_id=54321,
                           import_timestamp=datetime.datetime.now(),
                           is_compilation=True,
                           num_tracks=44)
        # Check that the correct key is automatically assigned.
        self.assertEqual(models.Album.get_key_name(54321), alb.key().name())
        # Check the artist_name property.
        self.assertEqual(alb._COMPILATION_ARTIST_NAME, alb.artist_name)

    def test_track(self):
        # Check key generation against a known case.
        self.assertEqual(u"djdb/t:test ufid",
                         models.Track.get_key_name("test ufid"))

        alb = models.Album(title='test album',
                           album_id=12345,
                           import_timestamp=datetime.datetime.now(),
                           album_artist=self.test_artist,
                           num_tracks=13)
        trk = models.Track(ufid="test ufid",
                           album=alb,
                           sampling_rate_hz=44100,
                           bit_rate_kbps=320,
                           channels='stereo',
                           duration_ms=123456,
                           title="test track",
                           track_num=4)
        # Check that the ufid property works properly.
        self.assertEqual("test ufid", trk.ufid)
        # Our human-readable duration is truncated to the nearest second.
        self.assertEqual("2:03", trk.duration)
        # Check that the artist_name property works when no track_artist
        # has been set.
        self.assertEqual(self.test_artist.name, trk.artist_name)
        # Check that the unicode representation of the object is the track
        # name.
        self.assertEqual("test track", unicode(trk))

        # Set a separate artist for this track, then check that the
        # artist_name property still works.
        trk_art = models.Artist(name='Track Artist')
        trk_art.save()
        trk.track_artist = trk_art
        self.assertEqual(trk.track_artist.name, trk.artist_name)

    def test_album_sorted_tracks(self):
        art = models.Artist(name='Test Artist')
        art.save()
        alb = models.Album(title='test album',
                           album_id=12345,
                           import_timestamp=datetime.datetime.now(),
                           album_artist=art,
                           num_tracks=6)
        alb.save()
        # Add our test tracks in a fixed but random order.
        test_track_nums = (4, 2, 1, 3, 6, 5)
        for track_num in test_track_nums:
            trk = models.Track(ufid="test ufid %d" % track_num,
                               album=alb,
                               sampling_rate_hz=44100,
                               bit_rate_kbps=320,
                               channels='stereo',
                               duration_ms=123456,
                               title="test track %d" % track_num,
                               track_num=track_num)
            trk.save()
        # Make sure the tracks come back in proper sort order.
        self.assertEqual(sorted(test_track_nums),
                         [trk.track_num for trk in alb.sorted_tracks])
