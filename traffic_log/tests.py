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
import os
import time
import unittest

from django import http
from django.test.client import Client

from auth import roles
from auth.models import User
from traffic_log import views, models, constants

class TrafficLogTestCase(unittest.TestCase):
    def setUp(self):
        self.admin_u = User(email='test')
        self.admin_u.roles.append(roles.TRAFFIC_LOG_ADMIN)
    
        self.dj_u = User(email='test2')
        self.dj_u.roles.append(roles.DJ)

        self.user_u = User(email='test3')

    def test_trafficlog_roles(self):
        self.assertTrue(self.admin_u.is_traffic_log_admin)
        self.assertTrue(self.dj_u.is_dj)
        self.assertTrue(self.user_u.is_active)


    def test_spot_constraint_assign(self):
        user = User(email='test')
        user.save()
        spot_key = models.Spot(title='test',body='body',type='Live Read Promo', author=user).put()
        constraint_key = models.SpotConstraint(dow=1,hour=1,slot=0).put()
        views.connectConstraintsAndSpot([constraint_key], spot_key)
        self.assertEqual(models.Spot.get(spot_key).constraints.count(), 1)

    def test_traffic_log_generate(self):
        pass

    def test_spot_logging(self):
        pass
    
    def test_spot_constraint_delete(self):
        pass

# """
# >>> import views, models, constants
# >>> from chirpradio.auth import User, KeyStorage, roles
# >>> from google.appengine.ext import db

# >>> user = User(email='test')
# >>> user.save()
# datastore_types.Key.from_path(u'User', 1, _app=u'chirpradio')

# 1
# """
# # delete constraint
# # expiration
# # get spots for time
# # delete spot
# # admin rol
