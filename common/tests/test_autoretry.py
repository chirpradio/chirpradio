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
import auth
from auth.models import User
from google.appengine.ext import db
from common.autoretry import AutoRetry

__all__ = ['TestAutoRetry']

class TestAutoRetry(unittest.TestCase):
    
    def setUp(self):
        for u in User.all():
            u.delete()
    
    def test_basic_query_functionality(self):
        # We should be able to pass in a model object or a queryset to AutoRetry and get the expected result.

        dj = User(email="test")
        dj.roles.append(auth.roles.DJ)
        AutoRetry(dj).put()
        self.assertTrue(dj)

        q = db.Query(User).filter("email =", "test")
        count = AutoRetry(q).count(1)
        self.assertEqual(count, 1)
        record_set = AutoRetry(q).fetch(1000)
        self.assertEqual([u.email for u in record_set], ['test'])

