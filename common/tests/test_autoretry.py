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

from __future__ import with_statement
import unittest

import fudge
from google.appengine.ext import db
from google.appengine.datastore import datastore_pb
from google.appengine.runtime import apiproxy_errors

import auth
from auth.models import User
from common.autoretry import AutoRetry
from common import autoretry

__all__ = ['TestAutoRetryQueryInterface', 'TestAutoRetryExceptionHandling']
    
def put_user():
    dj = User(email="test")
    dj.roles.append(auth.roles.DJ)
    dj.put()

class TestAutoRetryQueryInterface(unittest.TestCase):
    
    def setUp(self):
        for u in User.all():
            u.delete()
    
    def test_put(self):
        dj = User(email="test")
        dj.roles.append(auth.roles.DJ)
        AutoRetry(dj).put()
        self.assertTrue(dj)
        q = db.Query(User).filter("email =", "test")
        self.assertEqual([u.email for u in q], ['test'])
    
    def test_query_fetch(self):
        put_user()
        q = db.Query(User).filter("email =", "test")
        count = AutoRetry(q).count(1)
        self.assertEqual(count, 1)
        record_set = AutoRetry(q).fetch(1000)
        self.assertEqual([u.email for u in record_set], ['test'])
    
    def test_iterate_query(self):
        put_user()
        q = db.Query(User).filter("email =", "test")
        count = AutoRetry(q).count(1)
        self.assertEqual(count, 1)
        self.assertEqual([u.email for u in AutoRetry(q)], ['test'])
    
    def test_fetch_query_by_index(self):
        put_user()
        q = db.Query(User).filter("email =", "test")
        count = AutoRetry(q).count(1)
        self.assertEqual(count, 1)
        self.assertEqual([AutoRetry(q)[0].email], ['test'])
    
    def test_fetch_query_by_slice(self):
        put_user()
        q = db.Query(User).filter("email =", "test")
        count = AutoRetry(q).count(1)
        self.assertEqual(count, 1)
        self.assertEqual([u.email for u in AutoRetry(q)[0:15]], ['test'])

class TestAutoRetryExceptionHandling(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def tearDown(self):
        fudge.clear_expectations()
    
    def test_timeout(self):
        
        timeout = apiproxy_errors.ApplicationError(
                                        datastore_pb.Error.TIMEOUT,
                                        error_detail='just timed out, ur f**cked')
        FakeUser = (fudge.Fake('User')
                        .expects('fetch')
                        .raises(timeout)
                        .next_call()
                        .raises(timeout)
                        .next_call()
                        .raises(timeout)
                        .next_call()
                        .raises(timeout)
                        .next_call()
                        .raises(timeout)
                        .next_call()
                        .returns(['<user>']))
        
        fake_time = fudge.Fake('time').expects('sleep')
        
        with fudge.patched_context(autoretry, 'time', fake_time):
            record_set = AutoRetry(FakeUser).fetch(1000)
            self.assertEquals([u for u in record_set], ['<user>'])
        
        fudge.verify()
    
    def test_transaction_failed(self):
        
        failed_transaction = apiproxy_errors.ApplicationError(
                                        datastore_pb.Error.CONCURRENT_TRANSACTION,
                                        error_detail='dude, that transaction was bunk')
        FakeUser = (fudge.Fake('User')
                        .expects('fetch')
                        .raises(failed_transaction)
                        .next_call()
                        .raises(failed_transaction)
                        .next_call()
                        .raises(failed_transaction)
                        .next_call()
                        .raises(failed_transaction)
                        .next_call()
                        .raises(failed_transaction)
                        .next_call()
                        .returns(['<user>']))
        
        fake_time = fudge.Fake('time').expects('sleep')
        
        with fudge.patched_context(autoretry, 'time', fake_time):
            record_set = AutoRetry(FakeUser).fetch(1000)
            self.assertEquals([u for u in record_set], ['<user>'])
        
        fudge.verify()
    
    def test_cannot_wrap_an_autory_object(self):
        class Bob(object):
            pass
        
        def wrap_twice():
            a = AutoRetry(Bob())
            b = AutoRetry(a)
        self.assertRaises(ValueError, wrap_twice)
        
