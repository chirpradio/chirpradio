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
from datetime import timedelta
import csv
from StringIO import StringIO

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
        
        spot_copy = models.SpotCopy(body='body',
                                    spot=spot,
                                    author=user)
        spot_copy.put()
        
        resp = self.client.get(reverse('traffic_log.index'))
        context = resp.context[0]
        spot_map = {}
        constraint_map = {}
        for c in context['slotted_spots']:
            spot_map[c.hour] = list(c.iter_spots())[0]
            constraint_map[c.hour] = c
        
        now = time_util.chicago_now()
        
        # first hour:
        self.assertEqual(spot_map[now.hour].title, 'Legal ID')
        # second hour:
        self.assertEqual(spot_map[(now + datetime.timedelta(hours=1)).hour].title, 
                'Legal ID')
        # thir hour (not shown anymore):
        # self.assertEqual(spot_map[(now + datetime.timedelta(hours=2)).hour].title, 
        #         'Legal ID')

class TestTrafficLogAdminViews(FormTestCaseHelper, DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.TRAFFIC_LOG_ADMIN, roles.DJ])
    
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
        
        # spot shows up in DJ view:
        resp = self.client.get(reverse('traffic_log.index'))
        context = resp.context[0]
        slotted_spots = [c for c in context['slotted_spots']]
        spots = [s.title for s in slotted_spots[0].iter_spots()]
        self.assertEqual(spots[0], spot.title)
        
        # spot shows up in admin view:
        resp = self.client.get(reverse('traffic_log.listSpots'))
        context = resp.context[0]
        spots = [c.title for c in context['spots']]
        self.assertEqual(spots, ['Legal ID'])
    
    def test_spot_copy_expires_when_randomly_shuffled(self):
        # make a regular spot:
        resp = self.client.post(reverse('traffic_log.createSpot'), {
            'title': 'Legal ID',
            'type': 'Station ID',
            'hourbucket': '0,24',
            'dow_list': [str(d) for d in range(1,8)],
            'slot': '0'
        })
        self.assertNoFormErrors(resp)
        spot = models.Spot.all().filter("title =", "Legal ID").fetch(1)[0]
        
        resp = self.client.post(reverse('traffic_log.createSpotCopy'), {
            'spot_key': spot.key(),
            'body': 'You are listening to chirprario.odg',
            'underwriter': 'pretend this is an underwriter',
            # null expiration date for now:
            'expire_on': ''
        })
        self.assertNoFormErrors(resp)
        
        # spot shows up in DJ view:
        resp = self.client.get(reverse('traffic_log.index'))
        context = resp.context[0]
        slotted_spots = [c for c in context['slotted_spots']]
        spots = [s.title for s in slotted_spots[0].iter_spots()]
        self.assertEqual(spots[0], spot.title)
        
        # make the copy expire:
        spot_copy = spot.all_spot_copy()[0]
        spot_copy.expire_on = datetime.datetime.now()
        spot_copy.save()
        
        # it should be hidden now:
        resp = self.client.get(reverse('traffic_log.index'))
        context = resp.context[0]
        spots = []
        for slotted_spot in context['slotted_spots']:
            spots.append([s.title for s in slotted_spot.iter_spots()])
            
        self.assertEqual(spots, [[], []]) # ensure 2 hours of spots have expired
    
    def test_delete_spot(self):
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        self.assertEqual(spot.active, True)
        
        author = User(email='test')
        author.put()
        spot_copy = models.SpotCopy(body='body',
                                    spot=spot,
                                    author=author)
        spot_copy.put()
        
        # assign it to every day of the week at the top of the hour:
        constraint_keys = views.saveConstraint(dict(hourbucket="0,24", dow_list=range(1,8), slot=0))
        views.connectConstraintsAndSpot(constraint_keys, spot.key())
        
        resp = self.client.get(reverse('traffic_log.index'))
        context = resp.context[0]
        slotted_spots = [c for c in context['slotted_spots']]
        spots = [s.title for s in slotted_spots[0].iter_spots()]
        self.assertEqual(spots[0], spot.title)
                            
        resp = self.client.get(reverse('traffic_log.deleteSpot', args=[spot.key()]))
        
        # datastore was cleaned up:
        saved_spot = models.Spot.get(spot.key())
        self.assertEqual(saved_spot.active, False)
        
        saved_constaints = [s for s in models.SpotConstraint.get(constraint_keys)]
        active_spots = []
        for constraint in saved_constaints:
            for spot in constraint.iter_spots():
                active_spots.append(spot)
        self.assertEqual(len(active_spots), 0)
        
        # spot is hidden from landing page:
        resp = self.client.get(reverse('traffic_log.index'))
        context = resp.context[0]
        slotted_spots = [c for c in context['slotted_spots']]
        active_spots = []
        for slot in slotted_spots:
            for spot in slot.iter_spots_at_constraint():
                active_spots.append(spot)
        self.assertEqual(active_spots, [])
        
        # spot is hidden from admin view:
        resp = self.client.get(reverse('traffic_log.listSpots'))
        context = resp.context[0]
        spots = [c.title for c in context['spots']]
        self.assertEqual(spots, [])
    
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
    
    def test_delete_spot_copy(self):
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID')
        spot.put()
        dow=1 
        hour=0
        slot=0
        constraint = models.SpotConstraint(dow=dow, hour=hour, slot=slot, spots=[spot.key()])
        constraint.put()
        
        author = User(email='test')
        author.put()
        spot_copy = models.SpotCopy(
                        body='First',
                        spot=spot,
                        author=author)
        spot_copy.put()
        
        self.assertEqual(spot.get_spot_copy(dow, hour, slot)[0].body, "First")
        
        # now edit the second one:
        resp = self.client.get(reverse('traffic_log.deleteSpotCopy', args=(spot_copy.key(),)))
        
        self.assertEqual([c for c in spot.all_spot_copy()], [])
        
        self.assertEqual(spot.get_spot_copy(dow, hour, slot), (None, False))
    
    def test_move_spot_copy_to_another_spot(self):
        
        # See http://code.google.com/p/chirpradio/issues/detail?id=124
        dow=1 
        hour=0
        slot=0
        
        spot1 = models.Spot(
                        title='First Spot',
                        type='Station ID')
        spot1.put()
        spot1_key = spot1.key()
        constraint = models.SpotConstraint(dow=dow, hour=hour, slot=slot, spots=[spot1.key()])
        constraint.put()
        
        spot2 = models.Spot(
                        title='Second Spot',
                        type='Station ID')
        spot2.put()
        constraint = models.SpotConstraint(dow=dow, hour=hour, slot=slot, spots=[spot2.key()])
        constraint.put()
        
        # assign it to the first one:
        author = User(email='test')
        author.put()
        spot_copy = models.SpotCopy(
                        body='First',
                        spot=spot1,
                        author=author)
        spot_copy.put()
        
        self.assertEqual(spot1.get_spot_copy(dow, hour, slot)[0].body, "First")
        
        # now move it to the second spot:
        resp = self.client.post(reverse('traffic_log.editSpotCopy', args=(spot_copy.key(),)), {
            'spot_key': spot2.key(),
            'body': 'Second',
            'underwriter': '',
            'expire_on': ''
        })
        self.assertNoFormErrors(resp)
        
        self.assertEqual(spot2.get_spot_copy(dow, hour, slot)[0].body, "Second")
        
        spot1 = models.Spot.get(spot1_key)
        self.assertEqual(spot1.get_spot_copy(dow, hour, slot)[0], None)
    
    def test_random_spot_copy_during_creation_and_after_finishing(self):
        author = User(email='test')
        author.save()
        spot = models.Spot(
                        title='PSA',
                        type='Live Read PSA')
        spot.put()
        first_constraint = models.SpotConstraint(dow=1, hour=0, slot=0, spots=[spot.key()])
        first_constraint.put()
        second_constraint = models.SpotConstraint(dow=1, hour=1, slot=0, spots=[spot.key()])
        second_constraint.put()
        
        psa_copy = ['check out our store', 'turn off the stream', 'sharkula is the greatest']
        for body in psa_copy:
            resp = self.client.post(spot.get_add_copy_url(), {
                'underwriter': '',
                'expire_on': '',
                'body': body,
                'spot_key': spot.key()
            })
            self.assertNoFormErrors(resp)
            self.assertEqual(resp.status_code, 302)
        
        def get_read_context(constraint):
            resp = self.client.get(reverse('traffic_log.spotTextForReading', args=(spot.key(),)), {
                'hour': constraint.hour,
                'dow': constraint.dow,
                'slot': constraint.slot
            })
            self.assertEqual(resp.status_code, 200)
            context = resp.context
            return context
        
        first_random_copy = get_read_context(first_constraint)['spot_copy'].body
        assert first_random_copy in psa_copy
        # each subsequent reading should show the same:
        self.assertEqual(get_read_context(first_constraint)['spot_copy'].body, first_random_copy)
        self.assertEqual(get_read_context(first_constraint)['spot_copy'].body, first_random_copy)
        
        resp = self.client.get(get_read_context(first_constraint)['url_to_finish_spot'])
        self.assertEqual(resp.status_code, 200)
        logged = models.TrafficLogEntry.all().fetch(1)[0]
        self.assertEqual(logged.spot.key(), spot.key())
        
        # after finishing, copy should be the same for the first slot:
        next_random_copy = get_read_context(first_constraint)['spot_copy'].body
        self.assertEqual(next_random_copy, first_random_copy)
        # but cannot be finished:
        self.assertEqual(get_read_context(first_constraint)['url_to_finish_spot'], None)
        
        # after finishing, copy should be DIFFERENT for the next slot:
        next_random_copy = get_read_context(second_constraint)['spot_copy'].body
        self.assertNotEqual(next_random_copy, first_random_copy)
        self.assertNotEqual(get_read_context(second_constraint)['url_to_finish_spot'], None)
    
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
    
    def test_view_spot_for_reading_basic(self):
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
        
        resp = self.client.get(reverse('traffic_log.spotTextForReading', args=(spot.key(),)), {
            'hour': constraint.hour,
            'dow': constraint.dow,
            'slot': constraint.slot
        })
        context = resp.context
        # already finished, no need for finish URL:
        self.assertEqual(context['url_to_finish_spot'], None)
        assert '(already finished)' in resp.content
    
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

    
class TestTrafficLogReport(FormTestCaseHelper, DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.TRAFFIC_LOG_ADMIN])
        
        author = User(email='test')
        author.save()
        spot = models.Spot(
                        title='Legal ID',
                        type='Station ID', 
                        author=author)
        self.spot = spot
        spot.put()
        
        # make a constraint closest to now:
        now = time_util.chicago_now()
        today = now.date()
        current_hour = now.hour
        
        dow = today.isoweekday()
        self.dow = dow
        hour = current_hour
        slot = 0
        
        constraint = models.SpotConstraint(
            dow=dow, hour=hour, slot=slot, spots=[spot.key()])
        constraint.put()
        spot_copy = models.SpotCopy(
                        body='You are listening to chirpradio.org',
                        spot=spot,
                        author=author)
        self.spot_copy = spot_copy
        spot_copy.put()
        spot.random_spot_copies = [spot_copy.key()]
        spot.save()
        
        logged_spot = models.TrafficLogEntry(
            log_date = today,
            spot = spot_copy.spot,
            spot_copy = spot_copy,
            dow = dow,
            hour = hour,
            slot = slot,
            scheduled = constraint,
            readtime = time_util.chicago_now(), 
            reader = author
        )
        logged_spot.put()
    
    def test_download_report_of_all_spots(self):
        
        from_date = datetime.date.today() - timedelta(days=1)
        to_date = datetime.date.today() + timedelta(days=1)
        
        response = self.client.post(reverse('traffic_log.report'), {
            'start_date': from_date,
            'end_date': to_date,
            'type': constants.SPOT_TYPE_CHOICES[0], # all
            'underwriter': '',
            'download': 'Download'
        })
        self.assertNoFormErrors(response)
        
        self.assertEquals(response['Content-Type'], 'text/csv; charset=utf-8')
        
        report = csv.reader(StringIO(response.content))
        self.assertEquals(
            ['readtime', 'dow', 'slot_time', 'underwriter', 'title', 'type', 'excerpt'],
            report.next())
        row = report.next()
        
        self.assertEquals(row[1], constants.DOW_DICT[self.dow])
        self.assertEquals(row[4], self.spot.title)
        self.assertEquals(row[5], self.spot.type)
        self.assertEquals(row[6], self.spot_copy.body)

class TestAddHour(unittest.TestCase):
    
    def test_12am_on_sunday_becomes_1am(self):
        self.assertEqual(views.add_hour(0, 0), (1, 0))
        
    def test_1am_on_sunday_becomes_2am(self):
        self.assertEqual(views.add_hour(1, 0), (2, 0))
        
    def test_11pm_on_monday_becomes_12am_tuesday(self):
        self.assertEqual(views.add_hour(23, 1), (0, 2))
        
    def test_11pm_on_sunday_becomes_12am_monday(self):
        self.assertEqual(views.add_hour(23, 7), (0, 1))
