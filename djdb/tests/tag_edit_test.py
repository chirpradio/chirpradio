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

import unittest
from google.appengine.ext import db
from auth import User
from djdb import models


class TagEditTestCase(unittest.TestCase):

    def test_basic(self):
        user = User(email="foo@bar.com")
        user.save()
        class MockObj(db.Model):
            import_tags = []
        obj = MockObj()
        obj.import_tags = ["Foo", "Bar"]
        obj.save()
        self.assertEqual(set(obj.import_tags),
                         models.TagEdit.fetch_and_merge(obj))

        te1 = models.TagEdit(subject=obj, author=user)
        te1.added  = ["Baz"]
        te1.save()
        self.assertEqual(set(["Foo", "Bar", "Baz"]),
                         models.TagEdit.fetch_and_merge(obj))

        te2 = models.TagEdit(subject=obj, author=user)
        te2.added  = ["Zap"]
        te2.removed = ["Baz"]
        te2.save()
        self.assertEqual(set(["Foo", "Bar", "Zap"]),
                         models.TagEdit.fetch_and_merge(obj))
