
"""base testing components"""

from django.test import TestCase
from chirp.volunteers.management.commands.initgroups import initgroups

def eq_(value, expected_value):
    assert value==expected_value, (
        "%r != %r" % (value, expected_value))

class CoordinatorLoginTest(TestCase):
    
    ## fixme: stub out the login method instead?
    
    def setUp(self):
        super(CoordinatorLoginTest, self).setUp()
        initgroups(quiet=True)
        assert self.client.login(username='coordtest', password='test') # True if can login
    
    def tearDown(self):
        super(CoordinatorLoginTest, self).tearDown()
        self.client.logout()

class VolunteerLoginTest(TestCase):
    
    def setUp(self):
        super(VolunteerLoginTest, self).setUp()
        initgroups(quiet=True)
        assert self.client.login(username='volunteertest', password='test') # True if can login
    
    def tearDown(self):
        super(VolunteerLoginTest, self).tearDown()
        self.client.logout()
    