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
from djdb import tag_util


class TagUtilTestCase(unittest.TestCase):

    def assertExpectedTags(self, expected_tags, alb):
        self.assertEqual(expected_tags,
                         set(alb.current_tags))
        self.assertEqual(expected_tags,
                         set(models.TagEdit.fetch_and_merge(alb)))

    def test_basic_edits(self):
        # Create a test artist and album.
        test_artist = models.Artist(name=u"Test Artist")
        test_artist.save()
        alb = models.Album(title='test album',
                           album_id=12345,
                           import_timestamp=datetime.datetime.now(),
                           album_artist=test_artist,
                           num_tracks=7)
        alb.save()

        # Create a test user.
        user = User(email="test")
        user.save()

        expected_tags = set()

        # Add a tag.
        expected_tags.add("foo")
        self.assertTrue(tag_util.add_tag_and_save(user, alb, "foo"))
        self.assertExpectedTags(expected_tags, alb)
        
        # Adding the same tag again is a no-op.
        self.assertFalse(tag_util.add_tag_and_save(user, alb, "foo"))
        self.assertExpectedTags(expected_tags, alb)

        # Set a list of tags.
        expected_tags.add("bar")
        expected_tags.add("baz")
        self.assertTrue(tag_util.set_tags_and_save(user, alb,
                                                   list(expected_tags)))
        self.assertExpectedTags(expected_tags, alb)

        # Setting the same list again is a no-op
        self.assertFalse(tag_util.set_tags_and_save(user, alb,
                                                    list(expected_tags)))
        self.assertExpectedTags(expected_tags, alb)

        # Remove a tag.
        expected_tags.discard("bar")
        self.assertTrue(tag_util.remove_tag_and_save(user, alb, "bar"))
        self.assertExpectedTags(expected_tags, alb)

        # Removing the same tag again is a no-op.
        self.assertFalse(tag_util.remove_tag_and_save(user, alb, "bar"))
        self.assertExpectedTags(expected_tags, alb)

        # Simultaneous add and remove
        expected_tags.add("boom")
        expected_tags.discard("baz")
        self.assertTrue(tag_util.modify_tags_and_save(
                user, alb, ["boom"], ["baz"]))
        self.assertExpectedTags(expected_tags, alb)

        # Same add/remove again is a no-op.
        self.assertFalse(tag_util.modify_tags_and_save(
                user, alb, ["boom"], ["baz"]))
        self.assertExpectedTags(expected_tags, alb)


        
        
        
