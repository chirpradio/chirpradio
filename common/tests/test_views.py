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
import time

from django.test import TestCase
from google.appengine.api import memcache
from gaetestbed import TaskQueueTestCase

from common.models import Config, DBConfig


class TestViews(TaskQueueTestCase, TestCase):

    def setUp(self):
        super(TestViews, self).setUp()
        assert memcache.flush_all()

    def tearDown(self):
        super(TestViews, self).tearDown()
        assert memcache.flush_all()

    def test_warmup(self):
        dbconfig = DBConfig()
        dbconfig['foo'] = 'bar'
        assert memcache.flush_all()

        r = self.client.get('/_ah/warmup')
        self.assertEquals(r.status_code, 200)
        self.assertTasksInQueue(1, url='/api/current_playlist')
        for c in Config.all():
            c.delete()
        self.assertEqual(dbconfig['foo'], 'bar')
