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

import datetime
import unittest
from auth.models import User
from djdb import models
from djdb import search
from djdb import tag_util
from django.test.client import Client


class TagUtilTestCase(unittest.TestCase):
    def setUp(self):
        # Get user.
        self.client = Client()
        self.user = models.User.all().filter('email =', 'test@test.com')[0]

        # Create a test artist and album.
        self.artist = models.Artist(name=u"Test Artist")
        self.artist.save()
        self.album = models.Album(title='test album',
                                  album_id=12345,
                                  import_timestamp=datetime.datetime.now(),
                                  album_artist=self.artist,
                                  num_tracks=7)
        self.album.save()

    def tearDown(self):
        self.album.delete()
        self.artist.delete()
        
    def assertExpectedTags(self, expected_tags, album):
        self.assertEqual(expected_tags,
                         set(album.current_tags))
        self.assertEqual(expected_tags,
                         set(models.TagEdit.fetch_and_merge(album)))

    def test_basic_edits(self):
        expected_tags = set()

        # Add a tag.
        expected_tags.add(u"foo")
        self.assertTrue(tag_util.add_tag_and_save(self.user, self.album, u"foo"))
        self.assertExpectedTags(expected_tags, self.album)
        
        # Adding the same tag again is a no-op.
        self.assertFalse(tag_util.add_tag_and_save(self.user, self.album, u"foo"))
        self.assertExpectedTags(expected_tags, self.album)

        # Set a list of tags.
        expected_tags.add(u"bar")
        expected_tags.add(u"baz")
        self.assertTrue(tag_util.set_tags_and_save(self.user, self.album,
                                                   list(expected_tags)))
        self.assertExpectedTags(expected_tags, self.album)

        # Setting the same list again is a no-op
        self.assertFalse(tag_util.set_tags_and_save(self.user, self.album,
                                                    list(expected_tags)))
        self.assertExpectedTags(expected_tags, self.album)

        # Remove a tag.
        expected_tags.discard(u"bar")
        self.assertTrue(tag_util.remove_tag_and_save(self.user, self.album, u"bar"))
        self.assertExpectedTags(expected_tags, self.album)

        # Removing the same tag again is a no-op.
        self.assertFalse(tag_util.remove_tag_and_save(self.user, self.album, u"bar"))
        self.assertExpectedTags(expected_tags, self.album)

        # Simultaneous add and remove
        expected_tags.add(u"boom")
        expected_tags.discard(u"baz")
        self.assertTrue(tag_util.modify_tags_and_save(
                self.user, self.album, [u"boom"], [u"baz"]))
        self.assertExpectedTags(expected_tags, self.album)

        # Same add/remove again is a no-op.
        self.assertFalse(tag_util.modify_tags_and_save(
                self.user, self.album, [u"boom"], [u"baz"]))
        self.assertExpectedTags(expected_tags, self.album)

    def test_search_tags(self):
        # No tag.
        matches = search.simple_music_search(u"tag:Electro")
        self.assertEqual(len(matches), 0)
        
        # Add a tag.
        tag_util.add_tag_and_save(self.user, self.album, u"Electro")
        matches = search.simple_music_search(u"tag:Electro")
        self.assertEqual(matches['Album'][0].title, 'test album')

        # Remove a tag.
        tag_util.remove_tag_and_save(self.user, self.album, u"Electro")
        matches = search.simple_music_search(u"tag:Electro")
        self.assertEqual(len(matches), 0)
