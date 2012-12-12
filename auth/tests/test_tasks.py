from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson as json

from nose.tools import eq_

from auth import roles
from auth.models import User


class TestSyncUser(TestCase):
    user = {'name_first': 'Ivan',
            'name_last': u'Krsti\u0107',
            'nick': u'DJ Krsti\u0107',
            'member_id': 1,
            'email': 'person@chirpradio.org'}

    def setUp(self):
        self.url = reverse('auth.tasks.sync_user')

    def tearDown(self):
        for ob in User.all():
            ob.delete()

    def sync(self):
        resp = self.client.post(self.url,
                                {'user': json.dumps(self.user)})
        eq_(resp.status_code, 200)

    def test_sync_new(self):
        self.sync()
        us = User.all()[0]
        eq_(us.first_name, self.user['name_first'])
        eq_(us.last_name, self.user['name_last'])
        eq_(us.email, self.user['email'])
        eq_(us.dj_name, self.user['nick'])
        eq_(us.external_id, self.user['member_id'])
        eq_(us.is_superuser, False)
        eq_(us.is_active, True)
        eq_(us.roles, [roles.DJ])

    def test_sync_existing_with_id(self):
        us = User(email=self.user['email'],
                  external_id=self.user['member_id'])
        us.put()
        self.sync()
        us = User.all().filter('__key__ =', us.key()).fetch(1)[0]
        eq_(us.first_name, self.user['name_first'])
        eq_(us.last_name, self.user['name_last'])
        eq_(us.email, self.user['email'])
        eq_(us.dj_name, self.user['nick'])
        eq_(us.external_id, self.user['member_id'])
        eq_(us.is_superuser, False)
        eq_(us.is_active, True)
        eq_(us.roles, [roles.DJ])

    def test_sync_existing_without_id(self):
        us = User(email=self.user['email'])
        us.put()
        self.sync()
        us = User.all().filter('__key__ =', us.key()).fetch(1)[0]
        eq_(us.first_name, self.user['name_first'])
        eq_(us.last_name, self.user['name_last'])
        eq_(us.email, self.user['email'])
        eq_(us.dj_name, self.user['nick'])
        eq_(us.external_id, self.user['member_id'])
        eq_(us.is_superuser, False)
        eq_(us.is_active, True)
        eq_(us.roles, [roles.DJ])

    def test_sync_existing_with_roles(self):
        us = User(email=self.user['email'],
                  external_id=self.user['member_id'],
                  roles=[roles.REVIEWER])
        us.put()
        self.sync()
        us = User.all().filter('__key__ =', us.key()).fetch(1)[0]
        eq_(set(us.roles), set((roles.DJ, roles.REVIEWER)))

    def test_sync_existing_with_dj_role(self):
        us = User(email=self.user['email'],
                  external_id=self.user['member_id'],
                  roles=[roles.DJ, roles.REVIEWER])
        us.put()
        self.sync()
        us = User.all().filter('__key__ =', us.key()).fetch(1)[0]
        eq_(set(us.roles), set((roles.DJ, roles.REVIEWER)))

    def test_preserve_superuser(self):
        us = User(email=self.user['email'],
                  external_id=self.user['member_id'],
                  is_superuser=True)
        us.put()
        self.sync()
        us = User.all().filter('__key__ =', us.key()).fetch(1)[0]
        eq_(us.is_superuser, True)


class TestDeactivateUser(TestCase):

    def setUp(self):
        self.url = reverse('auth.tasks.deactivate_user')

    def tearDown(self):
        for ob in User.all():
            ob.delete()

    def test_deactivate(self):
        us = User(email='foo@bar.com', external_id=23)
        us.put()

        resp = self.client.post(self.url, {'external_id': 23})
        eq_(resp.status_code, 200)
        us = User.all().filter('__key__ =', us.key()).fetch(1)[0]
        eq_(us.is_active, False)

    def test_deactivate_no_user_by_id(self):
        us = User(email='foo@bar.com')
        us.put()

        resp = self.client.post(self.url, {'external_id': 23})
        eq_(resp.status_code, 200)

    def test_deactivate_non_existant(self):
        resp = self.client.post(self.url, {'external_id': 23})
        eq_(resp.status_code, 200)
