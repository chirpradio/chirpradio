# -*- coding: utf-8 -*-

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
from google.appengine.ext import db

from djdb import models
from djdb import search


class SearchTestCase(unittest.TestCase):

    def tearDown(self):
       # Purge the datastore of SearchMatches between tests.
       for x in models.SearchMatches.all().fetch(limit=1000):
           x.delete()

    def test_scrub(self):
        self.assertEqual(u"", search.scrub(u""))
        self.assertEqual(u"    ", search.scrub(u" \t\n\r"))

        self.assertEqual(u"foo", search.scrub(u"foo"))
        self.assertEqual(u"foo123", search.scrub(u"foo123"))

        self.assertEqual(u"foo ", search.scrub(u"Foo!"))
        self.assertEqual(u"oao", search.scrub(u"Øåø"))

        # Interior periods should be collapsed.
        self.assertEqual(u"la ", search.scrub(u"L.A."))
        self.assertEqual(u"gg  allen", search.scrub(u"G.G. Allen"))

    def test_explode(self):
        self.assertEqual([u"foo", u"bar"], search.explode(u"  foo \t  bar "))
        self.assertEqual([u"foo", u"bar", u"17"],
                         search.explode(u"foo-bar 17"))
        # Check that we filter out stop words when exploding a string.
        self.assertEqual([u"foo"], search.explode(u"the foo"))
        self.assertEqual([u"foo"], search.explode(u"foo, the"))

    def test_parse_query_string(self):
        # Check that we can handle the empty query.
        self.assertEqual([], search._parse_query_string(u""))
        self.assertEqual([], search._parse_query_string(u"   \r  \t\n  "))

        # Check some simple cases are handled correctly.
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo")],
            search._parse_query_string(u"foo"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo"),
             (search.IS_REQUIRED, search.IS_TERM, u"bar")],
            search._parse_query_string(u"Foo BaR!"))
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo")],
            search._parse_query_string(u"-Foo"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_PREFIX, u"foo")],
            search._parse_query_string(u"Foo*"))
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo"),
             (search.IS_REQUIRED, search.IS_PREFIX, u"bar")],
            search._parse_query_string(u"-Foo Bar*"))

        # Make sure that - and * are stripped out and treated like whitespace
        # unless they appear at the beginning or end of a string.
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo"),
             (search.IS_REQUIRED, search.IS_TERM, u"bar"),
             (search.IS_REQUIRED, search.IS_TERM, u"baz"),
             (search.IS_REQUIRED, search.IS_TERM, u"zoo"),
             ],
            search._parse_query_string(u"foo-bar baz*zoo"))

        # Duplicate -s and *s are ignored.
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo"),
             (search.IS_REQUIRED, search.IS_PREFIX, u"bar")],
            search._parse_query_string(u"---Foo Bar*****"))

        # Check that we filter out stop words, but only in the case of
        # terms.
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo")],
            search._parse_query_string(u"foo the"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo")],
            search._parse_query_string(u"foo -the"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo"),
             (search.IS_REQUIRED, search.IS_PREFIX, u"the")],
            search._parse_query_string(u"foo the*"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo"),
             (search.IS_FORBIDDEN, search.IS_PREFIX, u"the")],
            search._parse_query_string(u"foo -the*"))

        # Check some corner cases.
        self.assertEqual([], search._parse_query_string(u"- * -*"))
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo")],
            search._parse_query_string(u"-*,-Foo"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_PREFIX, u"foo")],
            search._parse_query_string(u"FOO!!!--*"))

    def test_basic_indexing_and_search(self):
        key1 = db.Key.from_path("kind_Foo", "key1")
        key2 = db.Key.from_path("kind_Foo", "key2")
        key3 = db.Key.from_path("kind_Bar", "key3")
        key4 = db.Key.from_path("kind_Bar", "key4")

        idx = search.Indexer()
        idx.add_key(key1, [u"alpha beta"])
        idx.add_key(key2, [u"alpha delta"])
        idx.save()

        idx = search.Indexer()
        idx.add_key(key3, [u"alpha gamma"])
        idx.add_key(key4, [u"alaska"])
        idx.save()

        self.assertEqual(set([key1, key2, key3]), 
                         search.fetch_keys_for_one_term("alpha"))

        self.assertEqual(
            set([key1, key2]),
            search.fetch_keys_for_one_term("alpha", entity_kind="kind_Foo"))

        self.assertEqual(set([key1]),
                         search.fetch_keys_for_one_term("beta"))

        self.assertEqual(0, len(search.fetch_keys_for_one_term("unknown")))


        self.assertEqual(set([key1, key2, key3]), 
                         search.fetch_keys_for_one_prefix("alpha"))
        self.assertEqual(set([key1, key2, key3, key4]), 
                         search.fetch_keys_for_one_prefix("al"))

        self.assertEqual(0, len(search.fetch_keys_for_one_prefix("unknown")))

    def test_search_using_queries(self):
        key1 = db.Key.from_path("kind_Foo", "key1")
        key2 = db.Key.from_path("kind_Foo", "key2")
        key3 = db.Key.from_path("kind_Foo", "key3")
        key4 = db.Key.from_path("kind_Bar", "key4")
        key5 = db.Key.from_path("kind_Bar", "key5")
        key6 = db.Key.from_path("kind_Bar", "key6")

        idx = search.Indexer()
        idx.add_key(key1, [u"alpha beta"])
        idx.add_key(key2, [u"alpha delta"])
        idx.add_key(key3, [u"alaska beta"])
        idx.add_key(key4, [u"beta delta"])
        idx.add_key(key5, [u"alpha alaska"])
        idx.add_key(key6, [u"delta gamma"])
        idx.save()

        # Check that some simple queries are handled correctly.
        self.assertEqual(
            set([key1, key2, key5]),
            search.fetch_keys_for_query_string(u"alpha"))
        self.assertEqual(
            set([key2, key4, key6]),
            search.fetch_keys_for_query_string(u"delta"))
        self.assertEqual(
            set([key1, key2, key3, key5]),
            search.fetch_keys_for_query_string(u"al*"))
        self.assertEqual(
            set([key1]),
            search.fetch_keys_for_query_string(u"beta alpha"))
        self.assertEqual(
            set([key1, key3]),
            search.fetch_keys_for_query_string(u"al* beta"))
        self.assertEqual(
            set([key2, key5]),
            search.fetch_keys_for_query_string(u"al* -beta"))
        self.assertEqual(
            set([key4, key6]),
            search.fetch_keys_for_query_string(u"delta -al*"))

        # Check that entity kind restrictions are respected.
        self.assertEqual(
            set([key1, key2]),
            search.fetch_keys_for_query_string(u"alpha",
                                               entity_kind="kind_Foo"))
        self.assertEqual(
            set([key5]),
            search.fetch_keys_for_query_string(u"al*", entity_kind="kind_Bar"))
        self.assertEqual(
            set([key2]),
            search.fetch_keys_for_query_string(u"al* -beta",
                                               entity_kind="kind_Foo"))

        # Check that searches against unknown terms are handled properly.
        self.assertEqual(
            set(),
            search.fetch_keys_for_query_string(u"nosuchterm"))
        self.assertEqual(
            set(),
            search.fetch_keys_for_query_string(u"nosuchterm*"))
        self.assertEqual(
            set(),
            search.fetch_keys_for_query_string(u"alpha nosuchterm"))
        self.assertEqual(
            set(),
            search.fetch_keys_for_query_string(u"alpha nosuchterm*"))
        self.assertEqual(
            set([key1, key2, key5]),
            search.fetch_keys_for_query_string(u"alpha -nosuchterm"))
        self.assertEqual(
            set([key1, key2, key5]),
            search.fetch_keys_for_query_string(u"alpha -nosuchterm*"))


        # Check that None is returned for various invalid/bogus queries.
        self.assertEqual(None, search.fetch_keys_for_query_string(u""))
        self.assertEqual(None, search.fetch_keys_for_query_string(u"+,,,*"))
        self.assertEqual(None, search.fetch_keys_for_query_string(u"-foo"))

    def test_object_indexing(self):
        # Create some test artists.
        art1 = models.Artist(name=u"Fall, The")
        art1.save()
        art2 = models.Artist(name=u"Eno, Brian")
        art2.save()
        # Create some test single-artist albums.
        alb1 = models.Album(title=u"This Nation's Saving Grace",
                            album_id=12345,
                            import_timestamp=datetime.datetime.now(),
                            album_artist=art1,
                            num_tracks=123)
        trk1 = []
        for i, track_title in enumerate(
            (u"Mansion", u"Bombast", u"Cruiser's Creek", u"What You Need",
             u"Spoiled Victorian Child", u"L.A.")):
            trk1.append(models.Track(ufid="test1-%d" % i,
                                     album=alb1,
                                     sampling_rate_hz=44110,
                                     bit_rate_kbps=320,
                                     channels="stereo",
                                     duration_ms=123,
                                     title=track_title,
                                     track_num=i+1))
        alb2 = models.Album(title=u"Another Green World",
                            album_id=67890,
                            import_timestamp=datetime.datetime.now(),
                            album_artist=art2,
                            num_tracks=456)
        trk2 = []
        for i, track_title in enumerate(
            (u"Sky Saw", u"Over Fire Island", u"St. Elmo's Fire",
             u"In Dark Trees", u"The Big Ship")):
            trk2.append(models.Track(ufid="test2-%d" % i,
                                     album=alb2,
                                     sampling_rate_hz=44110,
                                     bit_rate_kbps=192,
                                     channels="joint_stereo",
                                     duration_ms=456,
                                     title=track_title,
                                     track_num=i+1))
        # Create a test album that is a compilation.
        alb3 = models.Album(title=u"R&B Gold: 1976",
                            album_id=76543,
                            import_timestamp=datetime.datetime.now(),
                            is_compilation=True,
                            num_tracks=789)
        trk3_art = []
        trk3 = []
        for i, (artist_name, track_title) in enumerate(
            ((u"Earth, Wind & Fire", u"Sing A Song"),
             (u"Diana Ross", u"Love Hangover"),
             (u"Aretha Franklin", u"Something He Can Feel"),
             (u"KC & the Sunshine Band",
              u"(Shake, Shake, Shake) Shake Your Booty"))):
            art = models.Artist(name=artist_name)
            art.save()
            trk3_art.append(art)
            trk3.append(models.Track(ufid="test3-%d" % i,
                                     album=alb3,
                                     sampling_rate_hz=44110,
                                     bit_rate_kbps=128,
                                     channels="mono",
                                     duration_ms=789,
                                     title=track_title,
                                     track_artist=art,
                                     track_num=i+1))

        # Now index everything we just created.
        idx = search.Indexer()
        idx.add_artist(art1)
        idx.add_artist(art2)
        for art in trk3_art:
            idx.add_artist(art)

        idx.add_album(alb1)
        idx.add_album(alb2)
        idx.add_album(alb3)

        for trk in trk1 + trk2 + trk3:
            idx.add_track(trk)

        idx.save()

        # Now do some test searches.
        self.assertEqual(
            # This query matches the album and all of the tracks.
            set([alb1.key()] + [t.key() for t in trk1]),
            search.fetch_keys_for_query_string(u"nations"))
        self.assertEqual(
            set([alb1.key()]),
            search.fetch_keys_for_query_string(u"nations",
                                               entity_kind="Album"))
        
        self.assertEqual(
            # The query "fire" should match:
            #   * Two of the songs from "Another Green World"
            #   * The band "Earth, Wind & Fire"
            #   * The EW&F track from the compilation.
            set([trk2[1].key(), trk2[2].key(),
                 trk3_art[0].key(), trk3[0].key()]),
            search.fetch_keys_for_query_string(u"fire"))