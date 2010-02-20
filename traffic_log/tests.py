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
    for x in models.TrafficLogEntry.all():
        x.delete()
    for c in models.SpotCopy.all():
        c.delete()
    for s in models.Spot.all():
        s.delete()
    for c in models.SpotConstraint.all():
        c.delete()

class TestTrafficLogViews(DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
    
    def tearDown(self):
        clear_data()
    
    def test_landing_page_shows_spots(self):
        user = User(email='test')
        user.save()
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot_key = spot.put()
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
        
        self.assertEqual(spot_map[now.hour].title, 'Legal ID')
        self.assertEqual(spot_map[(now + datetime.timedelta(hours=1)).hour].title, 
                'Legal ID')
        self.assertEqual(spot_map[(now + datetime.timedelta(hours=2)).hour].title, 
                'Legal ID')
        
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
        author = User(email='test')
        author.put()
        spot_copy = models.SpotCopy(body='body',
                                    spot=spot,
                                    author=author)
        spot_copy.put()
        spot.random_spot_copies = [spot_copy.key()]
        spot.save()

        self.assertEqual(constraint_map[(1L, 12L, 0L)].url_to_finish_spot(spot), 
            "/traffic_log/spot-copy/%s/finish?hour=12&dow=1&slot=0" % spot_copy.key())
            
        self.assertEqual(constraint_map[(1L, 12L, 0L)].as_query_string(), 
            "hour=12&dow=1&slot=0")
    
    def test_create_spot_copy(self):
        dow = 1
        hour = 0
        slot = 0
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        constraint = models.SpotConstraint(dow=dow, hour=hour, slot=slot, spots=[spot.key()])
        constraint.put()
        
        resp = self.client.post(reverse('traffic_log.createSpotCopy'), {
            'spot_key': spot.key(),
            'body': 'You are listening to chirprario.odg',
            'underwriter': 'pretend this is an underwriter',
            'expire_on': ''
        })
        self.assertNoFormErrors(resp)
        
        spot_copy, is_logged = spot.get_spot_copy(dow, hour, slot)
        self.assertEqual(spot_copy.body, 'You are listening to chirprario.odg')
        self.assertEqual(spot_copy.underwriter, 'pretend this is an underwriter')
        self.assertEqual(spot_copy.author.email, 'test@test.com')
    
    def test_edit_spot_copy(self):
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        constraint = models.SpotConstraint(dow=1, hour=0, slot=0, spots=[spot.key()])
        constraint.put()
        
        author = User(email='test')
        author.put()
        spot_copy = models.SpotCopy(
                        body='First',
                        spot=spot,
                        author=author)
        spot_copy.put()
        spot_copy2 = models.SpotCopy(
                        body='You are listening to chirpradio.org',
                        spot=spot,
                        author=author)
        spot_copy2.put()
        
        # now edit the second one:
        resp = self.client.post(reverse('traffic_log.editSpotCopy', args=(spot_copy2.key(),)), {
            'spot_key': spot.key(),
            'body': 'Something else entirely',
            'underwriter': 'another underwriter',
            'expire_on': ''
        })
        self.assertNoFormErrors(resp)
        
        spot_copy = [c for c in spot.all_spot_copy()]
        self.assertEqual([c.body for c in spot_copy], ['First','Something else entirely'])
        self.assertEqual([c.underwriter for c in spot_copy], [None, 'another underwriter'])
        self.assertEqual([c.author.email for c in spot_copy], ['test', 'test@test.com'])
    
    def test_make_spot_copy_expire(self):
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        constraint = models.SpotConstraint(dow=1, hour=0, slot=0, spots=[spot.key()])
        constraint.put()
        
        author = User(email='test')
        author.put()
        spot_copy = models.SpotCopy(
                        body='First',
                        spot=spot,
                        author=author)
        spot_copy.put()
        
        resp = self.client.post(reverse('traffic_log.editSpotCopy', args=(spot_copy.key(),)), {
            'spot_key': spot.key(),
            'body': 'Something else entirely',
            'underwriter': 'another underwriter',
            'expire_on': '2/5/2010' # any date in the past
        })
        self.assertNoFormErrors(resp)
        
        spot_copy = [c for c in spot.all_spot_copy()]
        self.assertEqual(spot_copy, [])
    
    def test_create_edit_spot_copy_expiry(self):
        dow = 1
        hour = 0
        slot = 0
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        constraint = models.SpotConstraint(dow=dow, hour=hour, slot=slot, spots=[spot.key()])
        constraint.put()
        
        now = time_util.chicago_now() + datetime.timedelta(hours=2)
        resp = self.client.post(reverse('traffic_log.views.addCopyForSpot', args=(spot.key(),)), {
            'spot_key': spot.key(),
            'body': 'You are listening to chirprario.odg',
            'underwriter': 'pretend this is an underwriter',
            'expire_on': now.strftime("%m/%d/%Y %H:%M:%S") # no timezone info
        })
        self.assertNoFormErrors(resp)
        
        spot_copy, is_logged = spot.get_spot_copy(dow, hour, slot)
        converted_expire_on = time_util.convert_utc_to_chicago(spot_copy.expire_on)
        self.assertEqual(converted_expire_on.timetuple(), now.timetuple())
        
        resp = self.client.post(reverse('traffic_log.editSpotCopy', args=(spot_copy.key(),)), {
            'spot_key': spot.key(),
            'body': 'You are listening to chirprario.odg',
            'underwriter': 'pretend this is an underwriter',
            'expire_on': spot_copy.expire_on.strftime("%m/%d/%Y %H:%M:%S") # no timezone info
        })
        self.assertNoFormErrors(resp)
        
        spot_copy, is_logged = spot.get_spot_copy(dow, hour, slot)
        converted_expire_on = time_util.convert_utc_to_chicago(spot_copy.expire_on)
        self.assertEqual(converted_expire_on.timetuple(), now.timetuple())
    
    def test_delete_spot_copy(self):
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        constraint = models.SpotConstraint(dow=1, hour=0, slot=0, spots=[spot.key()])
        constraint.put()
        
        author = User(email='test')
        author.put()
        spot_copy = models.SpotCopy(
                        body='First',
                        spot=spot,
                        author=author)
        spot_copy.put()
        
        # now edit the second one:
        resp = self.client.get(reverse('traffic_log.deleteSpotCopy', args=(spot_copy.key(),)))
        
        self.assertEqual([c for c in spot.all_spot_copy()], [])

class TestObjects(DjangoTestCase):
    
    def test_spot_copy(self):
        author = User(email='test')
        author.save()
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        self.assertEqual(spot.get_add_copy_url(), 
                            reverse('traffic_log.views.addCopyForSpot', args=(spot.key(),)))
        
        constraint = models.SpotConstraint(dow=1, hour=0, slot=0, spots=[spot.key()])
        constraint.put()
        
        spot_copy = models.SpotCopy(
                        body=(
                            'You are now and forever listening to a killer '
                            'radio station called chirpradio.org'),
                        spot=spot,
                        author=author)
        spot_copy.put()
        
        self.assertEqual(str(spot_copy), "You are now and forever listening to a killer radio...")
        self.assertEqual(spot_copy.get_edit_url(), 
                            reverse('traffic_log.editSpotCopy', args=(spot_copy.key(),)))
        self.assertEqual(spot_copy.get_delete_url(), 
                            reverse('traffic_log.deleteSpotCopy', args=(spot_copy.key(),)))

class TestTrafficLogDJViews(FormTestCaseHelper, DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="dj-test@test.com", roles=[roles.DJ])
    
    def tearDown(self):
        clear_data()
    
    def test_view_spot_for_reading(self):
        author = User(email='test')
        author.save()
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        constraint = models.SpotConstraint(dow=1, hour=0, slot=0, spots=[spot.key()])
        constraint.put()
        
        spot_copy = models.SpotCopy(
                        body='You are listening to chirpradio.org',
                        spot=spot,
                        author=author)
        spot_copy.put()
        
        resp = self.client.get(reverse('traffic_log.spotTextForReading', args=(spot.key(),)), {
            'hour': constraint.hour,
            'dow': constraint.dow,
            'slot': constraint.slot
        })
        context = resp.context
        self.assertEqual(context['spot_copy'].body, 'You are listening to chirpradio.org')
        self.assertEqual(context['url_to_finish_spot'], 
            "/traffic_log/spot-copy/%s/finish?hour=0&dow=1&slot=0" % spot_copy.key())

    def test_finish_spot(self):
        self.assertEqual(list(models.TrafficLogEntry.all().fetch(5)), [])
        
        author = User(email='test')
        author.save()
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID', 
                        author=author)
        spot.put()
        
        # make a constraint closest to now:
        now = time_util.chicago_now()
        today = now.date()
        current_hour = now.hour
        constraint = models.SpotConstraint(
            dow=today.isoweekday(), hour=current_hour, slot=0, spots=[spot.key()])
        constraint.put()
        
        spot_copy = models.SpotCopy(
                        body='You are listening to chirpradio.org',
                        spot=spot,
                        author=author)
        spot_copy.put()
        
        spot.random_spot_copies = [spot_copy.key()]
        spot.save()
        
        resp = self.client.get(reverse('traffic_log.index'))
        # unfinished spot should have been marked in static HTML:
        assert '<tr class="new">' in resp.content
        
        resp = self.client.get(reverse('traffic_log.finishReadingSpotCopy', args=(spot_copy.key(),)), {
            'hour': constraint.hour,
            'dow': constraint.dow,
            'slot': constraint.slot
        })
        logged = models.TrafficLogEntry.all().fetch(1)[0]
        self.assertEqual(logged.reader.email, "dj-test@test.com")
        self.assertEqual(logged.readtime.timetuple()[0:5], datetime.datetime.now().timetuple()[0:5])
        self.assertEqual(logged.log_date, time_util.chicago_now().date())
        self.assertEqual(logged.spot.key(), spot.key())
        self.assertEqual(logged.spot_copy.key(), spot_copy.key())
        self.assertEqual(logged.scheduled.key(), constraint.key())
        self.assertEqual(logged.hour, constraint.hour)
        self.assertEqual(logged.dow, constraint.dow)
        
        resp = self.client.get(reverse('traffic_log.index'))
        # finished spot should have been marked in static HTML:
        assert '<tr class="finished">' in resp.content
    
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


