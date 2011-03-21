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

from google.appengine.api import memcache

from common import dbconfig
from common.models import Config, load_dbconfig_into_memcache

__all__ = ['TestDBConfig']

class TestDBConfig(unittest.TestCase):
    
    def setUp(self):
        assert memcache.flush_all()
        for c in Config.all():
            c.delete()
    
    def test_non_existant_var(self):
        self.assertRaises(KeyError, lambda: dbconfig['not-here'])
    
    def test_set_and_get_var(self):
        dbconfig['something'] = 'some value'
        self.assertEqual(dbconfig['something'], 'some value')
        dbconfig['something'] = 'another value'
        self.assertEqual(dbconfig['something'], 'another value')
    
    def test_get(self):
        self.assertEqual(dbconfig.get('nonexistant'), None)
        self.assertEqual(dbconfig.get('nonexistant', 'default'), 'default')
        dbconfig['existing'] = 'true'
        self.assertEqual(dbconfig.get('existing'), 'true')
    
    def test_get_from_memcache(self):
        dbconfig['sticky'] = 'stuck'
        self.assertEqual(dbconfig['sticky'], 'stuck')
        for c in Config.all():
            c.delete()
        # should be in memcache:
        self.assertEqual(dbconfig['sticky'], 'stuck')
    
    def test_load_dbconfig_into_memcache(self):
        dbconfig['one'] = '1'
        dbconfig['two'] = '2'
        dbconfig['three'] = 'three'
        assert memcache.flush_all()
        load_dbconfig_into_memcache()
        for c in Config.all():
            c.delete()
        # should be in memcache:
        self.assertEqual(dbconfig['one'], '1')
        self.assertEqual(dbconfig['two'], '2')
        self.assertEqual(dbconfig['three'], 'three')
