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


class SearchHelpersTestCase(unittest.TestCase):

    def test_discard_items(self):
        items = range(10)
        # Check the common case.
        self.assertEqual(search._discard_items(items, 3), 3)
        self.assertEqual(len(items), 7)
        # Check discarding 0 items.
        self.assertEqual(search._discard_items(items, 0), 0)
        self.assertEqual(len(items), 7)
        # Check discarding a negative number of items.
        self.assertEqual(search._discard_items(items, -17), 0)
        self.assertEqual(len(items), 7)
        # Check discarding more items than actually exist.
        self.assertEqual(search._discard_items(items, 100), 7)
        self.assertEqual(len(items), 0)
        # Check discarding from None.
        self.assertEqual(search._discard_items(None, 17), 0)

    def test_enforce_results_limit_on_matches(self):
        matches = {"Artist": range(10), "Album": range(10), "Track": range(10)}
        # If the max_num_results is larger than the total number of matches,
        # do nothing.
        search._enforce_results_limit_on_matches(matches, 100)
        self.assertEqual(30, sum(len(x) for x in matches.values()))
        # If the max_num_results is None, do nothing.
        search._enforce_results_limit_on_matches(matches, None)
        self.assertEqual(30, sum(len(x) for x in matches.values()))
        # Track objects are the first to go.
        search._enforce_results_limit_on_matches(matches, 25)
        self.assertEqual(25, sum(len(x) for x in matches.values()))
        self.assertEqual(5, len(matches["Track"]))
        # Next we start dropping Album objects.
        search._enforce_results_limit_on_matches(matches, 12)
        self.assertEqual(12, sum(len(x) for x in matches.values()))
        self.assertEqual(2, len(matches["Album"]))
        # Empty lists are dropped entirely.
        self.assertTrue("Track" not in matches)
        # Artists are the last to go.
        search._enforce_results_limit_on_matches(matches, 5)
        self.assertEqual(5, sum(len(x) for x in matches.values()))
        self.assertEqual(5, len(matches["Artist"]))
        self.assertEqual(1, len(matches))


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

    def test_strip_tags(self):
        self.assertEqual("foo", search.strip_tags("foo"))
        self.assertEqual("foo ", search.strip_tags("foo [bar]"))

    def test_parse_query_string(self):
        # Check that we can handle the empty query.
        self.assertEqual([], search._parse_query_string(u""))
        self.assertEqual([], search._parse_query_string(u"   \r  \t\n  "))

        # Check some simple cases are handled correctly.
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo", None, None)],
            search._parse_query_string(u"foo"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo", None, None),
             (search.IS_REQUIRED, search.IS_TERM, u"bar", None, None)],
            search._parse_query_string(u"Foo BaR!"))
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo", None, None)],
            search._parse_query_string(u"-Foo"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_PREFIX, u"foo", None, None)],
            search._parse_query_string(u"Foo*"))
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo", None, None),
             (search.IS_REQUIRED, search.IS_PREFIX, u"bar", None, None)],
            search._parse_query_string(u"-Foo Bar*"))

        # Make sure that - and * are stripped out and treated like whitespace
        # unless they appear at the beginning or end of a string.
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo", None, None),
             (search.IS_REQUIRED, search.IS_TERM, u"bar", None, None),
             (search.IS_REQUIRED, search.IS_TERM, u"baz", None, None),
             (search.IS_REQUIRED, search.IS_TERM, u"zoo", None, None),
             ],
            search._parse_query_string(u"foo-bar baz*zoo"))

        # Duplicate -s and *s are ignored.
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo", None, None),
             (search.IS_REQUIRED, search.IS_PREFIX, u"bar", None, None)],
            search._parse_query_string(u"---Foo Bar*****"))

        # Check that we filter out stop words for all flavors.
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo", None, None)],
            search._parse_query_string(u"foo the"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo", None, None)],
            search._parse_query_string(u"foo -the"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo", None, None)],
            search._parse_query_string(u"foo the*"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_TERM, u"foo", None, None)],
            search._parse_query_string(u"foo -the*"))

        # Check some corner cases.
        self.assertEqual([], search._parse_query_string(u"- * -*"))
        self.assertEqual(
            [(search.IS_FORBIDDEN, search.IS_TERM, u"foo", None, None)],
            search._parse_query_string(u"-*,-Foo"))
        self.assertEqual(
            [(search.IS_REQUIRED, search.IS_PREFIX, u"foo", None, None)],
            search._parse_query_string(u"FOO!!!--*"))

        # Check field:value cases.
        self.assertEqual([(search.IS_REQUIRED, search.IS_TERM, u"2011", u"year", None)],
            search._parse_query_string(u"year:2011"))
        self.assertEqual([(search.IS_REQUIRED, search.IS_TERM, u"2000", u"year", u"2011")],
            search._parse_query_string(u"year:2000-2011"))
        self.assertEqual([(search.IS_REQUIRED, search.IS_PREFIX, u"rec", u"label", None)],
            search._parse_query_string(u"label:Rec*"))
        self.assertEqual([(search.IS_FORBIDDEN, search.IS_TERM, u"2011", u"year", None)],
            search._parse_query_string(u"-year:2011"))
        self.assertEqual([(search.IS_FORBIDDEN, search.IS_TERM, u"2000", u"year", u"2011")],
            search._parse_query_string(u"-year:2000-2011"))
        self.assertEqual([(search.IS_FORBIDDEN, search.IS_PREFIX, u"rec", u"label", None)],
            search._parse_query_string(u"-label:Rec*"))


    def test_basic_indexing_and_search(self):
        key1 = db.Key.from_path("kind_Foo", "key1")
        key2 = db.Key.from_path("kind_Foo", "key2")
        key3 = db.Key.from_path("kind_Bar", "key3")
        key4 = db.Key.from_path("kind_Bar", "key4")

        idx = search.Indexer()
        idx.add_key(key1, "f1", u"alpha beta")
        idx.add_key(key2, "f2", u"alpha delta")
        idx.save()

        idx = search.Indexer()
        idx.add_key(key3, "f1", u"alpha gamma")
        idx.add_key(key4, "f2", u"alaska")
        idx.save()

        self.assertEqual(set([(key1, "f1"), (key2, "f2"), (key3, "f1")]), 
                         search.fetch_keys_for_one_term("alpha"))

        self.assertEqual(
            set([(key1, "f1"), (key2, "f2")]),
            search.fetch_keys_for_one_term("alpha", entity_kind="kind_Foo"))

        self.assertEqual(
            set([(key1, "f1"), (key3, "f1")]),
            search.fetch_keys_for_one_term("alpha", field="f1"))

        self.assertEqual(set([(key1, "f1")]),
                         search.fetch_keys_for_one_term("beta"))

        self.assertEqual(0, len(search.fetch_keys_for_one_term("unknown")))

        self.assertEqual(set([(key1, "f1"), (key2, "f2"), (key3, "f1")]), 
                         search.fetch_keys_for_one_prefix("alpha"))
        self.assertEqual(set([(key1, "f1"), (key2, "f2"),
                              (key3, "f1"), (key4, "f2")]), 
                         search.fetch_keys_for_one_prefix("al"))
        self.assertEqual(set([(key2, "f2"), (key4, "f2")]), 
                         search.fetch_keys_for_one_prefix("al", field="f2"))

        self.assertEqual(0, len(search.fetch_keys_for_one_prefix("unknown")))

    def test_search_using_queries(self):
        key1 = db.Key.from_path("kind_Foo", "key1")
        key2 = db.Key.from_path("kind_Foo", "key2")
        key3 = db.Key.from_path("kind_Foo", "key3")
        key4 = db.Key.from_path("kind_Bar", "key4")
        key5 = db.Key.from_path("kind_Bar", "key5")
        key6 = db.Key.from_path("kind_Bar", "key6")
        key7 = db.Key.from_path("kind_Bar", "key7")

        idx = search.Indexer()
        idx.add_key(key1, "f1", u"alpha beta")
        idx.add_key(key2, "f2", u"alpha delta")
        idx.add_key(key3, "f1", u"alaska beta")
        idx.add_key(key4, "f2", u"beta delta")
        idx.add_key(key5, "f1", u"alpha alaska")
        idx.add_key(key6, "f2", u"delta gamma")
        # an indexed value ending in a stop word:
        idx.add_key(key7, "stop-word-prefix", u"something in")
        idx.save()

        # Check that some simple queries are handled correctly.
        self.assertEqual(
            {key1: set(["f1"]), key2: set(["f2"]), key5: set(["f1"])},
            search.fetch_keys_for_query_string(u"alpha"))
        self.assertEqual(
            {key2: set(["f2"]), key4: set(["f2"]), key6: set(["f2"])},
            search.fetch_keys_for_query_string(u"delta"))
        self.assertEqual(
            {key1: set(["f1"]), key2: set(["f2"]), key3: set(["f1"]),
             key5: set(["f1"])},
            search.fetch_keys_for_query_string(u"al*"))
        self.assertEqual(
            {key1: set(["f1"])},
            search.fetch_keys_for_query_string(u"beta alpha"))
        self.assertEqual(
            {key1: set(["f1"]), key3: set(["f1"])},
            search.fetch_keys_for_query_string(u"al* beta"))
        self.assertEqual(
            {key2: set(["f2"]), key5: set(["f1"])},
            search.fetch_keys_for_query_string(u"al* -beta"))
        self.assertEqual(
            {key4: set(["f2"]), key6: set(["f2"])},
            search.fetch_keys_for_query_string(u"delta -al*"))
        # Make sure we can run a prefix search on a stop word
        # (this is necessary for autocomplete searches)
        self.assertEqual(
            {key7: set(["stop-word-prefix"])},
            search.fetch_keys_for_query_string(u"something i*"))

        # Check that entity kind restrictions are respected.
        self.assertEqual(
            {key1: set(["f1"]), key2: set(["f2"])},
            search.fetch_keys_for_query_string(u"alpha",
                                               entity_kind="kind_Foo"))
        self.assertEqual(
            {key5: set(["f1"])},
            search.fetch_keys_for_query_string(u"al*", entity_kind="kind_Bar"))
        self.assertEqual(
            {key2: set(["f2"])},
            search.fetch_keys_for_query_string(u"al* -beta",
                                               entity_kind="kind_Foo"))

        # Check that searches against unknown terms are handled properly.
        self.assertEqual(
            {},
            search.fetch_keys_for_query_string(u"nosuchterm"))
        self.assertEqual(
            {},
            search.fetch_keys_for_query_string(u"nosuchterm*"))
        self.assertEqual(
            {},
            search.fetch_keys_for_query_string(u"alpha nosuchterm"))
        self.assertEqual(
            {},
            search.fetch_keys_for_query_string(u"alpha nosuchterm*"))
        self.assertEqual(
            {key1: set(["f1"]), key2: set(["f2"]), key5: set(["f1"])},
            search.fetch_keys_for_query_string(u"alpha -nosuchterm"))
        self.assertEqual(
            {key1: set(["f1"]), key2: set(["f2"]), key5: set(["f1"])},
            search.fetch_keys_for_query_string(u"alpha -nosuchterm*"))

        # Check that None is returned for various invalid/bogus queries.
        self.assertEqual(None, search.fetch_keys_for_query_string(u""))
        self.assertEqual(None, search.fetch_keys_for_query_string(u"+,,,*"))
        self.assertEqual(None, search.fetch_keys_for_query_string(u"-foo"))

    def test_object_indexing(self):
        idx = search.Indexer()

        # Create some test artists.
        art1 = models.Artist(name=u"Fall, The", parent=idx.transaction,
                             key_name="art1")
        art2 = models.Artist(name=u"Eno, Brian", parent=idx.transaction,
                             key_name="art2")
        # Create some test single-artist albums.
        alb1 = models.Album(title=u"This Nation's Saving Grace",
                            year=1985,
                            album_id=12345,
                            label=u"Some Label",
                            import_timestamp=datetime.datetime.now(),
                            album_artist=art1,
                            num_tracks=123,
                            parent=idx.transaction)
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
                                     track_num=i+1,
                                     parent=idx.transaction))
        alb2 = models.Album(title=u"Another Green World",
                            album_id=67890,
                            label=u"Some Label",
                            import_timestamp=datetime.datetime.now(),
                            album_artist=art2,
                            num_tracks=456,
                            parent=idx.transaction)
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
                                     track_num=i+1,
                                     parent=idx.transaction))
        # Create a test album that is a compilation.
        alb3 = models.Album(title=u"R&B Gold: 1976",
                            album_id=76543,
                            label=u"Some Label",
                            import_timestamp=datetime.datetime.now(),
                            is_compilation=True,
                            num_tracks=789,
                            parent=idx.transaction)
        trk3_art = []
        trk3 = []
        for i, (artist_name, track_title) in enumerate(
            ((u"Earth, Wind & Fire", u"Sing A Song"),
             (u"Diana Ross", u"Love Hangover"),
             (u"Aretha Franklin", u"Something He Can Feel"),
             (u"KC & the Sunshine Band",
              u"(Shake, Shake, Shake) Shake Your Booty"))):
            art = models.Artist(name=artist_name,
                                key_name=artist_name,
                                parent=idx.transaction)
            trk3_art.append(art)
            trk3.append(models.Track(ufid="test3-%d" % i,
                                     album=alb3,
                                     sampling_rate_hz=44110,
                                     bit_rate_kbps=128,
                                     channels="mono",
                                     duration_ms=789,
                                     title=track_title,
                                     track_artist=art,
                                     track_num=i+1,
                                     parent=idx.transaction))

        # Now index everything we just created.
        idx.add_artist(art1)
        idx.add_artist(art2)
        for art in trk3_art:
            idx.add_artist(art)

        idx.add_album(alb1)
        idx.add_album(alb2)
        idx.add_album(alb3)

        for trk in trk1 + trk2 + trk3:
            idx.add_track(trk)

        idx.save()  # This also saves all of the objects.

        # Now do some test searches.

        # This query matches the album and all of the tracks.
        expected = {alb1.key(): set(["title"])}
        self.assertEqual(
            expected,
            search.fetch_keys_for_query_string(u"nations",
                                               entity_kind="Album"))
        for t in trk1:
            expected[t.key()] = set(["album"])
        self.assertEqual(
            expected,
            search.fetch_keys_for_query_string(u"nations"))

        # The query "fire" should match:
        #   * Two of the songs from "Another Green World"
        #   * The band "Earth, Wind & Fire"
        #   * The EW&F track from the compilation.
        expected = {
            trk2[1].key(): set(["title"]),
            trk2[2].key(): set(["title"]),
            trk3_art[0].key(): set(["name"]),
            trk3[0].key(): set(["artist"]),
            }
        self.assertEqual(
            expected,
            search.fetch_keys_for_query_string(u"fire"))

    def test_index_optimization(self):
        # Create a bunch of test keys.
        test_keys = [db.Key.from_path("kind_dummy", "key%02d" % i)
                     for i in range(12)]
        # Now create four test SearchMatches, all for the same term
        # and over two different fields.  Split the four sets of keys
        # between them.
        for i in range(4):
            sm = models.SearchMatches(generation=search._GENERATION,
                                      entity_kind="kind_dummy",
                                      field="field%d" % (i%2),
                                      term="foo")
            sm.matches.extend(test_keys[i::4])
            sm.save()
        # Optimize on our term
        num_deleted = search.optimize_index("foo")
        # We go from 4 objects to 2, so we should return 4-2=2.
        self.assertEqual(2, num_deleted)
        # There should now just one SearchMatches per field.
        sm = None
        query = models.SearchMatches.all().filter("term =", "foo")
        all_sms = sorted(query.fetch(999), key=lambda sm: sm.field)
        self.assertEqual(2, len(all_sms))
        for sm in all_sms:
            self.assertEqual(search._GENERATION, sm.generation)
            self.assertEqual("kind_dummy", sm.entity_kind)
            self.assertEqual("foo", sm.term)
        self.assertEqual("field0", all_sms[0].field)
        self.assertEqual(set(test_keys[0::2]), set(all_sms[0].matches))
        self.assertEqual("field1", all_sms[1].field)
        self.assertEqual(set(test_keys[1::2]), set(all_sms[1].matches))

        # Create a SearchMatches for a stop word.  Optimization should
        # cause that object to be deleted.
        sm = models.SearchMatches(generation=search._GENERATION,
                                  entity_kind="kind_dummy",
                                  field="field",
                                  term="the")
        sm.matches.extend(test_keys)
        sm.save()
        num_deleted = search.optimize_index("the")
        self.assertEqual(1, num_deleted)
        query = models.SearchMatches.all().filter("term =", "the")
        self.assertEqual(0, query.count())


class SearchTestCaseWithData(SearchTestCase):
    
    def setUp(self):
        idx = search.Indexer()
        # Create some test artists.
        art = models.Artist(name=u"beatles", parent=idx.transaction,
                            key_name="ss-art1")
        idx.add_artist(art)
        art = models.Artist(name=u"beatnicks", parent=idx.transaction,
                            key_name="ss-art2")
        idx.add_artist(art)
        art = models.Artist(name=u"beatnuts", parent=idx.transaction,
                            key_name="ss-art3")
        idx.add_artist(art)
        idx.save()
    
    def test_search_results_are_truncated(self):
        # Make sure that the max_num_results works properly.
        matches = search.simple_music_search(u"beat*", max_num_results=2,
                                             entity_kind='Artist')
        self.assertEquals(len(matches['Artist']), 2)

        # Now revoke one of the two matches
        revoked_art = matches['Artist'].pop()
        revoked_art.revoked = True
        revoked_art.save()

        # Now perform the same query again: we should get two results,
        # specifically the two items we didn't revoke.
        new_matches = search.simple_music_search(u"beat*", max_num_results=2,
                                                 entity_kind='Artist')
        self.assertEquals(len(new_matches['Artist']), 2)
        self.assertTrue(new_matches['Artist'][0].key() != revoked_art.key())
        self.assertTrue(new_matches['Artist'][1].key() != revoked_art.key())

        # Now revoke one more item and repeat the query.  The lone
        # unrevoked item should be the only result.
        new_matches["Artist"][0].revoked = True
        new_matches["Artist"][0].save()
        unrevoked_art = new_matches["Artist"][1]
        newer_matches = search.simple_music_search(u"beat*", max_num_results=2,
                                                   entity_kind='Artist')
        self.assertEquals(len(newer_matches['Artist']), 1)
        self.assertEquals(newer_matches['Artist'][0].key(),
                          unrevoked_art.key())


        



        
        
