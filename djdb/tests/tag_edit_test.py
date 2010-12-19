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
from auth import User, roles
from djdb import models
from django.test.client import Client

class TagEditTestCase(unittest.TestCase):
    def setUp(self):
        # Log in.
        self.client = Client()
        assert self.client.login(email='test@test.com', roles=[roles.DJ])
        
        # Get user.
        self.user = models.User.all().filter('email =', 'test@test.com')[0]
        
    def test_basic(self):
        class MockObj(db.Model):
            import_tags = []
        obj = MockObj()
        obj.import_tags = ["Foo", "Bar"]
        obj.save()
        self.assertEqual(set(obj.import_tags),
                         models.TagEdit.fetch_and_merge(obj))

        te1 = models.TagEdit(subject=obj, author=self.user)
        te1.added  = ["Baz"]
        te1.save()
        self.assertEqual(set(["Foo", "Bar", "Baz"]),
                         models.TagEdit.fetch_and_merge(obj))

        te2 = models.TagEdit(subject=obj, author=self.user)
        te2.added  = ["Zap"]
        te2.removed = ["Baz"]
        te2.save()
        self.assertEqual(set(["Foo", "Bar", "Zap"]),
                         models.TagEdit.fetch_and_merge(obj))

    def test_add(self):
        # Not music director.
        response = self.client.post("/djdb/tags/new", {'name': 'TestTag',
                                                       'description': 'descr'})
        self.assertEqual(response.status_code, 403)

        # Music director.
        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()
        response = self.client.post("/djdb/tags/new", {'name': 'TestTag',
                                                       'description': 'descr'})
        self.assertEqual(response.status_code, 302)

        tag = models.Tag.all().filter('name =', 'TestTag').fetch(1)[0]
        self.assertEqual(tag.description, 'descr')
        
    def test_edit(self):
        # Add a new tag.
        tag = models.Tag(name='TestTag',
                         description='descr')
        tag.put()
        
        # Not music director.
        response = self.client.post("/djdb/tag/TestTag",
                                    {'name': 'TestTag2',
                                     'description': 'descr2'})
        self.assertEqual(response.status_code, 403)

        # Music director.
        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()
        response = self.client.post("/djdb/tag/TestTag",
                                    {'name': 'TestTag2',
                                     'description': 'descr2'})
        self.assertEqual(response.status_code, 302)

        tag = models.Tag.all().filter('name =', 'TestTag2').fetch(1)[0]
        self.assertEqual(tag.description, 'descr2')

