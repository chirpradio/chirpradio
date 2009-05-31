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
import time
import unittest
from google.appengine.ext import db
from djdb import bulk_upload
from djdb import models
from djdb import search


class BulkUploadTestCase(unittest.TestCase):

    def setUp(self):
        self.test_artist_name = "Test Artist"
        self.test_artist = models.Artist(name=self.test_artist_name)
        self.test_artist.save()
        
    def tearDown(self):
        # Clean up any datastore objects that we created.
        for kind in (models.Artist, models.Album, models.Track,
                     models.SearchMatches):
            for x in kind.all().fetch(1000):
                x.delete()

    def test_lookup_artist(self):
        # Check that lookup fetches an artist out of the datastore, and
        # also stashes it in the passed-in cache dictionary.
        cache_dict = {}
        art = bulk_upload._lookup_artist(self.test_artist_name, cache_dict)
        self.assertEqual(self.test_artist_name, art.name)
        self.assertTrue(self.test_artist_name in cache_dict)
        self.assertEqual(art.key(), cache_dict[self.test_artist_name].key())

        # Check that we return None if we try to look up an unknown
        # artist.
        UNKNOWN_ARTIST = "Unknown Artist"
        art = bulk_upload._lookup_artist(UNKNOWN_ARTIST, cache_dict)
        self.assertTrue(art is None)

        # Check that we actually use our cache by adding an entry to it
        # for UNKNOWN_ARTIST.
        cache_dict[UNKNOWN_ARTIST] = self.test_artist
        art = bulk_upload._lookup_artist(UNKNOWN_ARTIST, cache_dict)
        self.assertTrue(art is not None)
        self.assertEqual(self.test_artist.key(), art.key())

    def test_decoding_album_and_track_lines_for_single_artist_album(self):
        timestamp = int(time.time())
        test_album_line = "\0".join((
                "ALB",
                # The last bit is the UTF-8 representation of \u1234.
                "My Album Title \xe1\x88\xb4",
                "12345",  # Album ID
                str(timestamp),
                self.test_artist_name,
                "6",  # Number of tracks
                ))
        txn = db.Key.from_path("test", "test transaction key")
        cache_dict = {}
        alb = bulk_upload._decode_album_line(test_album_line, txn, cache_dict)
        self.assertEqual(txn, alb.parent_key())
        # This also checks that we decode UTF-8 correctly.
        self.assertEqual(u"My Album Title \u1234", alb.title)
        self.assertEqual(12345, alb.album_id)
        self.assertEqual(datetime.datetime.utcfromtimestamp(timestamp),
                         alb.import_timestamp)
        self.assertFalse(alb.is_compilation)
        self.assertEqual(self.test_artist.key(), alb.album_artist.key())
        self.assertEqual(6, alb.num_tracks)
        
        test_track_line = "\0".join((
                "TRK",
                "test ufid",
                "My Track Title",
                "",  # No track artist
                "3",  # Track number
                "44100",  # Sampling rate
                "128",  # Bit rate
                "stereo",  # Channels
                "54321",  # Duration
                ))
        trk = bulk_upload._decode_track_line(test_track_line, alb, cache_dict)
        self.assertEqual(txn, trk.parent_key())
        self.assertEqual("test ufid", trk.ufid)
        self.assertEqual("My Track Title", trk.title)
        self.assertTrue(trk.track_artist is None)
        self.assertEqual(3, trk.track_num)
        self.assertEqual(44100, trk.sampling_rate_hz)
        self.assertEqual(128, trk.bit_rate_kbps)
        self.assertEqual("stereo", trk.channels)
        self.assertEqual(54321, trk.duration_ms)

    def test_decoding_album_and_track_lines_for_compilation(self):
        timestamp = int(time.time())
        test_album_line = "\0".join((
                "ALB",
                "My Album Title",  
                "12345",  # Album ID
                str(timestamp),
                "",  # No artist name specified
                "6",  # Number of tracks
                ))
        txn = db.Key.from_path("test", "test transaction key")
        cache_dict = {}
        alb = bulk_upload._decode_album_line(test_album_line, txn, cache_dict)
        self.assertTrue(alb.is_compilation)
        self.assertTrue(alb.album_artist is None)
        
        test_track_line = "\0".join((
                "TRK",
                "test ufid",
                "My Track Title",
                self.test_artist_name,  # Specifies a track artist.
                "3",  # Track number
                "44100",  # Sampling rate
                "128",  # Bit rate
                "stereo",  # Channels
                "54321",  # Duration
                ))
        trk = bulk_upload._decode_track_line(test_track_line, alb, cache_dict)
        self.assertEqual(self.test_artist.key(), trk.track_artist.key())

    def test_full_decode(self):
        timestamp = int(time.time())
        data_list = []
        ufid_counter = 0
        for alb_title in (("Test Album One", "Test Album Two")):
            data_list.append("\0".join((
                        "ALB",
                        alb_title,
                        str(abs(hash(alb_title))),  # Album ID
                        str(timestamp),
                        self.test_artist_name,
                        "3",  # Number of tracks
                        )))
            for track_num in (1, 2, 3):
                ufid_counter += 1
                data_list.append("\0".join((
                            "TRK",
                            "ufid %d" % ufid_counter,
                            "Track %d" % track_num,
                            "",  # No track artist
                            str(track_num),
                            "44100",  # Sampling rate
                            "128",  # Bit rate
                            "stereo",  # Channels
                            "54321",  # Duration
                            )))

        data = "\r\n".join(data_list)
        bulk_upload.decode_and_save(data)

        # Now do some searches and make sure that the correct number
        # of keys are fetched.
        self.assertEqual(
            1,
            len(search.fetch_keys_for_one_term("one", entity_kind="Album")))
        self.assertEqual(
            3,
            len(search.fetch_keys_for_one_term("one", entity_kind="Track")))
        self.assertEqual(
            1,
            len(search.fetch_keys_for_one_term("two", entity_kind="Album")))
        self.assertEqual(
            3,
            len(search.fetch_keys_for_one_term("two", entity_kind="Track")))
        
                            
                             
            
        

                
