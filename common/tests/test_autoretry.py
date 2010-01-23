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

import unittest, auth
from google.appengine.ext import db
from common.autoretry import AutoRetry

__all__ = ['TestAutoRetry']

def create_dj():
    dj = auth.models.User(email="test")
    dj.roles.append(auth.roles.DJ)
    dj.put()
    return dj

class TestAutoRetry(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def test_api(self):
        """We should be able to pass in a model object or a queryset to AutoRetry and get the expected result."""

        User = auth.models.User

        dj = User(email="test")
        dj.roles.append(auth.roles.DJ)
        AutoRetry(dj).put()
        self.assertTrue(dj)

        q = db.Query(User).filter("email =", "test")
        count = AutoRetry(q).count(1)
        record_set = AutoRetry(q).fetch(1000)
        self.assertEqual(record_set, 1)

