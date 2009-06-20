
"""tests actions that need to be performed by volunteers"""

from decimal import Decimal
import datetime
import unittest
from chirp.volunteers.admin import VolunteerAdminForm
from chirp.volunteers.forms import ResetPasswordForm
from chirp.volunteers.models import (
    User, Volunteer, Committee, Task, TaskType, TaskAssignment, TaskStatus, Event)
from django import forms
from django.test import TestCase
from django.utils import simplejson
from django.contrib.auth.models import User
from chirp.volunteers.tests.base import eq_, VolunteerLoginTest
from django.core import mail

__all__ = ['TestTaskManagement', 'TestPasswordReset']

class TestPasswordReset(TestCase):
    
    fixtures = ['users.json']
    
    def test_password_reset(self):
        user = User.objects.filter(username="volunteertest").all()[0]
        
        resp = self.client.post('/chirp/password_change/', {
            'email': user.email,
            'new_password1': "sooperhack",
            'new_password2': "sooperhack" 
        })
        self.assertRedirects(resp, "/chirp/password_change_done")
        
        # get a fresh connection:
        user = User.objects.filter(username="volunteertest").all()[0]
        assert user.check_password("sooperhack")
        
        eq_(len(mail.outbox), 1)
        msg = mail.outbox[0]
        eq_(msg.from_email, "kumar.mcmillan@gmail.com")
        eq_(msg.subject, "New password for CHIRP Volunteer Tracker")
        # print msg.body
        assert "volunteertest" in msg.body
        assert "sooperhack" in msg.body
        assert "http://example.com" in msg.body
        eq_(msg.to, [user.email])
        
    def test_wrong_email(self):
        f = ResetPasswordForm()
        f.cleaned_data= {'email': "not-a-known-email@elsewhere.com"}
        try:
            f.clean_email()
        except forms.ValidationError, err:
            eq_(err.messages, (
                ["No user exists with that email.  Please ask jenna@chirpradio.org "
                 "to add you to the volunteer tracker."]))
        else:
            raise AssertionError("Expected ValidationError")


class TestTaskManagement(VolunteerLoginTest):
    
    fixtures = ['users.json', 'event_tasks.json']
    
    def setUp(self):
        super(TestTaskManagement, self).setUp()
        # set all events from fixtures to be current:
        for event in Event.objects.all():
            event.start_date = datetime.datetime.now() + timedelta(days=7)
            event.save()
    
    def tearDown(self):
        super(TestTaskManagement, self).tearDown()
        for t in TaskAssignment.objects.all():
            t.delete()
    
    def test_show_tasks_for_claiming(self):
        resp = self.client.get('/chirp/tasks/claim/')
        context = resp.context[0]
        
        eq_(len(context['events']), 1)
        event = context['events'][0]
        eq_(event.name, "CHIRP Record Fair & Other Delights")
        
        tasks = [t for t in event.tasks]
        eq_(len(tasks), 3)
        eq_(tasks[0].task_type.short_description, "Tabling")
        eq_(tasks[0].claim_prompt, 
            "You are about to commit to Tabling on Sat Apr 18th "
            "from 9:00 a.m. - 10:00 a.m..")
        eq_(tasks[0].claimed_by, [User.objects.get(username='volunteertest')])
    
    def test_hide_tasks_for_claiming_when_event_not_ready(self):
        # make all tasks unready for claiming:
        for event in Event.objects.all():
            event.tasks_can_be_claimed = False
            event.save()
            
        resp = self.client.get('/chirp/tasks/claim/')
        context = resp.context[0]
        
        eq_(len(context['events']), 1)
        event = context['events'][0]
        eq_(event.name, "CHIRP Record Fair & Other Delights")
        eq_([t for t in event.tasks], [])
    
    def test_hide_expired_events(self):
        old_event = Event()
        old_event.name = "Pitchfork 2008"
        old_event.duration_days = 3
        # make it just expire by a day:
        old_event.start_date = datetime.datetime.now() - timedelta(days=4)
        old_event.save()
        
        some_task = Task()
        some_task.for_event = old_event
        some_task.for_committee = Committee.objects.filter(
                                            name="Events Committee").all()[0]
        some_task.task_type = TaskType.objects.filter(
                                            short_description="Tabling").all()[0]
        some_task.start_time = datetime.datetime.now() - timedelta(days=30)
        some_task.duration_minutes = 60
        some_task.num_volunteers = 1
        some_task.save()
        
        plainuser = User.objects.filter(username='plainuser').all()[0]
        temp_volunteer = Volunteer()
        temp_volunteer.user = plainuser
        temp_volunteer.save()
        
        asn = TaskAssignment()
        asn.task = some_task
        asn.points = 1
        asn.volunteer = temp_volunteer
        asn.save()
        
        resp = self.client.get('/chirp/tasks/claim/')
        context = resp.context[0]
        
        eq_(sorted(e.name for e in context['events']), 
            ['CHIRP Record Fair & Other Delights'])
        
    def test_claim_task(self):
        event = Event.objects.all()[0]
        tasks = [t for t in event.tasks]
        
        task_to_claim = tasks[2]
        
        # simulate ajax claim request :
        resp = self.client.get('/chirp/tasks/claim/%s.json' % task_to_claim.id)
        json = simplejson.loads(resp.content)
        # TODO(kumar): hmm, django test environment does not expose current user the same way.
        # eq_(json, {'user': ''})
        
        asn = TaskAssignment.objects.filter(task=task_to_claim)
        first_asn = asn[0]
        eq_(first_asn.task, task_to_claim)
        eq_(first_asn.task.for_event, event)
        eq_(first_asn.points, 3)
        
        eq_(len(mail.outbox), 1)
        msg = mail.outbox[0]
        eq_(msg.from_email, "kumar.mcmillan@gmail.com")
        eq_(msg.to, [first_asn.volunteer.user.email])
        eq_(msg.subject, "You have volunteered for a CHIRP task.")
        # print msg.body
        assert "CHIRP Record Fair & Other Delights" in msg.body
        assert "Tabling on Sat Apr 18th from 11:00 a.m. - 12:00 p.m." in msg.body
        
    def test_cant_claim_task_twice(self):
        event = Event.objects.all()[0]
        tasks = [t for t in event.tasks]
        
        task_to_claim = tasks[2]
        
        resp = self.client.get('/chirp/tasks/claim/%s.json' % task_to_claim.id)
        # interface shouldn't allow this but it's possible with two browser windows:
        resp = self.client.get('/chirp/tasks/claim/%s.json' % task_to_claim.id)
        json = simplejson.loads(resp.content)
        eq_(json['success'], False)
        eq_(json['error'], 
            "You have already claimed this task (Tabling on Sat Apr "
            "18th from 11:00 a.m. - 12:00 p.m.)")
    
    def test_cant_claim_task_beyond_alotted_slots(self):
        event = Event.objects.all()[0]
        
        some_task = Task()
        some_task.for_event = event
        some_task.for_committee = Committee.objects.filter(
                                            name="Events Committee").all()[0]
        some_task.task_type = TaskType.objects.filter(
                                            short_description="Tabling").all()[0]
        some_task.start_time = datetime.datetime(2009,4,18,9)
        some_task.duration_minutes = 60
        some_task.num_volunteers = 1
        some_task.save()
        
        plainuser = User.objects.filter(username='plainuser').all()[0]
        temp_volunteer = Volunteer()
        temp_volunteer.user = plainuser
        temp_volunteer.save()
        
        asn = TaskAssignment()
        asn.task = some_task
        asn.points = 1
        asn.volunteer = temp_volunteer
        asn.save()
        
        # should not be able to save
        resp = self.client.get('/chirp/tasks/claim/%s.json' % some_task.id)
        json = simplejson.loads(resp.content)
        eq_(json['success'], False)
        eq_(json['error'], 
            "All volunteers needed for this task have been filled "
            "(Tabling on Sat Apr 18th from 9:00 a.m. - 10:00 a.m.)")
        
    def test_claim_task_with_no_potential_points(self):
        event = Event.objects.all()[0]
        task_to_claim = Task()
        task_to_claim.for_committee = Committee.objects.all()[0]
        task_to_claim.task_type = TaskType.objects.all()[0]
        task_to_claim.for_event = event
        task_to_claim.save()
        
        resp = self.client.get('/chirp/tasks/claim/%s.json' % task_to_claim.id)
        json = simplejson.loads(resp.content)
        
        asn = TaskAssignment.objects.filter(task=task_to_claim)
        first_asn = asn[0]
        eq_(first_asn.task, task_to_claim)
        eq_(first_asn.task.for_event, event)
        eq_(first_asn.points, Decimal('1'))
        