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
import datetime

from django.core.urlresolvers import reverse
from django.test import TestCase as DjangoTestCase
from django import http
from django.test.client import Client

from common.testutil import FormTestCaseHelper
from common import time_util
from auth import roles
from auth.models import User
from traffic_log import views, models, constants

def clear_data():
    for x in models.TrafficLogEntry.all().fetch(1000):
        x.delete()
    for s in models.Spot.all().fetch(1000):
        s.delete()
    for c in models.SpotConstraint.all().fetch(1000):
        c.delete()

class TestTrafficLogViews(DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
    
    def tearDown(self):
        clear_data()
    
    def test_landing_page_shows_spots(self):
        user = User(email='test')
        user.save()
        spot_key = models.Spot(
                        title='Legal ID',
                        body='You are listening to chirpradio.org',
                        type='Station ID', 
                        author=user).put()
        # assign it to every day of the week at the top of the hour:
        constraint_keys = views.saveConstraint(dict(hourbucket="0,24", dow_list=range(1,8), slot=0))
        views.connectConstraintsAndSpot(constraint_keys, spot_key)
        
        resp = self.client.get(reverse('traffic_log.index'))
        context = resp.context[0]
        spot_map = {}
        constraint_map = {}
        for c in context['slotted_spots']:
            spot_map[c.hour] = list(c.iter_spots())[0]
            constraint_map[c.hour] = c
        
        now = time_util.chicago_now()
        
        self.assertEqual(spot_map[now.hour].body, 'You are listening to chirpradio.org')
        self.assertEqual(spot_map[(now + datetime.timedelta(hours=1)).hour].body, 
                'You are listening to chirpradio.org')
        self.assertEqual(spot_map[(now + datetime.timedelta(hours=2)).hour].body, 
                'You are listening to chirpradio.org')
        
        constraint = constraint_map[now.hour]
        spot = list(constraint.iter_spots())[0]
        assert constraint.url_to_finish_spot(spot) in resp.content

class TestTrafficLogAdminViews(FormTestCaseHelper, DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.TRAFFIC_LOG_ADMIN])
    
    def tearDown(self):
        clear_data()
    
    def test_create_spot(self):
        resp = self.client.post(reverse('traffic_log.createSpot'), {
            'title': 'Legal ID',
            'body': 'You are listening to chirpradio.org',
            'type': 'Station ID',
            'hourbucket': '0,24',
            'dow_list': [str(d) for d in range(1,8)],
            'slot': '0'
        })
        self.assertNoFormErrors(resp)
        spot = models.Spot.all().filter("title =", "Legal ID").fetch(1)[0]
        dow = set()
        hours = set()
        constraint_map = {}
        for constraint in spot.constraints:
            dow.add(constraint.dow)
            hours.add(constraint.hour)
            constraint_map[(constraint.dow, constraint.hour, constraint.slot)] = constraint
        self.assertEqual(sorted(dow), range(1,8))
        self.assertEqual(sorted(hours), range(0,24))
        
        # check with Sunday 12:00pm
        self.assertEqual(constraint_map[(1L, 12L, 0L)].url_to_finish_spot(spot), 
            "/traffic_log/spot/%s/finish?hour=12&dow=1&slot=0" % spot.key())

class TestTrafficLogDJViews(FormTestCaseHelper, DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="dj-test@test.com", roles=[roles.DJ])
    
    def tearDown(self):
        clear_data()

    def test_finish_spot(self):
        self.assertEqual(list(models.TrafficLogEntry.all().fetch(5)), [])
        
        author = User(email='test')
        author.save()
        spot = models.Spot(
                        title='Legal ID',
                        body='You are listening to chirpradio.org',
                        type='Station ID', 
                        author=author)
        spot.put()
        constraint = models.SpotConstraint(dow=1, hour=0, slot=0, spots=[spot.key()])
        constraint.put()
        
        resp = self.client.get(reverse('traffic_log.finishSpot', args=(spot.key(),)), {
            'hour': constraint.hour,
            'dow': constraint.dow,
            'slot': constraint.slot
        })
        logged = models.TrafficLogEntry.all().fetch(1)[0]
        self.assertEqual(logged.reader.email, "dj-test@test.com")
        self.assertEqual(logged.readtime.timetuple()[0:5], datetime.datetime.now().timetuple()[0:5])
        self.assertEqual(logged.log_date, time_util.chicago_now().date())
        self.assertEqual(logged.spot.key(), spot.key())
        self.assertEqual(logged.scheduled.key(), constraint.key())
        self.assertEqual(logged.hour, constraint.hour)
    
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
