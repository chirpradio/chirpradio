
"""tests Volunteer Coordinator administration"""

import datetime
import unittest
from chirp.volunteers.admin import VolunteerAdminForm
from chirp.volunteers.models import Volunteer, Committee, Task, TaskType, TaskAssignment, TaskStatus
from django import forms
from django.test import TestCase
from django.contrib.auth.models import User
from chirp.volunteers.tests.base import eq_, CoordinatorLoginTest

class TestVolunteerMgmt(CoordinatorLoginTest):
    
    fixtures = ['users.json', 'volunteers.json']
    def setUp(self):
        super(TestVolunteerMgmt, self).setUp()
    
    def tearDown(self):
        super(TestVolunteerMgmt, self).tearDown()
        for v in Volunteer.objects.all():
            v.delete()
        
    def test_create_volunteer(self):
        
        vol_count = 1
        v = Volunteer.objects.all()
        eq_(v.count(), vol_count)
        
        user = User.objects.filter(username='volunteertest')[0].id
        committees = []
        committees.append(Committee.objects.filter(name='Music Department')[0].id)
        committees.append(Committee.objects.filter(name='Tech Committee')[0].id)
        
        resp = self.client.post('/volunteers/volunteer/add/', {
            'user': user,
            'committees': committees,
        })
        eq_(resp.status_code, 302)
        assert resp['Location'].endswith("/volunteers/volunteer/"), (
                                    "unexpected redirect: %s" % resp['Location'])
        
        v = Volunteer.objects.all()
        eq_(v.count(), vol_count + 1)
        vol = v[0]
        eq_(vol.user.username, 'volunteertest')
        eq_(sorted([c.name for c in vol.committees.all()]), [u'Music Department', u'Tech Committee'])

class TestVolunteerValidation(TestCase):
    
    fixtures = ['users.json']
    
    def test_user_must_be_volunteer(self):
        user = User.objects.filter(username='plainuser')[0]
        
        f = VolunteerAdminForm()
        f.cleaned_data= {'user': user}
        try:
            f.clean_user()
        except forms.ValidationError, err:
            eq_(err.messages[0], (
                "User plainuser cannot be a volunteer because he/she is not "
                "in the Volunteer group (You can fix this in Home > Auth > "
                "Users under the Groups section)"))
        else:
            raise AssertionError("Expected ValidationError")
    
    def test_user_must_be_staff(self):
        user = User.objects.filter(username='plainuser_not_staff')[0]
        
        f = VolunteerAdminForm()
        f.cleaned_data= {'user': user}
        try:
            f.clean_user()
        except forms.ValidationError, err:
            eq_(err.messages[0], (
                "User plainuser_not_staff cannot be a volunteer because he/she "
                "has not been marked with Staff status (you can fix this in Home > "
                "Auth > Users under the Permissions section)"))
        else:
            raise AssertionError("Expected ValidationError")
        
class TestTaskMgmt(CoordinatorLoginTest):
    
    fixtures = ['users.json', 'volunteers.json', 'tasks.json']
    
    def test_create_task(self):
        
        vol_id = Volunteer.objects.all()[0].id
        committee_id = Committee.objects.filter(name='Tech Committee')[0].id
        task_id = Task.objects.filter(description='Ears&Eyes Fest at Hideout')[0].id
        task_status_id = TaskStatus.objects.filter(status='Assigned')[0].id
        
        resp = self.client.post('/volunteers/taskassignment/add/', {
            'volunteer': vol_id,
            'points': 1,
            'task': task_id,
            'status': task_status_id
        })
        # print resp.content
        eq_(resp.status_code, 302)
        assert resp['Location'].endswith("/volunteers/taskassignment/"), (
                                    "unexpected redirect: %s" % resp['Location'])
        
        task_asn = TaskAssignment.objects.all()[0]
        eq_(task_asn.volunteer.id, vol_id)
        eq_(task_asn.points, 1)
        eq_(task_asn.task.id, task_id)
        eq_(task_asn.status.id, task_status_id)
        