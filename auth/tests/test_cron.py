from datetime import date, datetime
from textwrap import dedent

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson as json

import fudge
from fudge.inspector import arg
from nose.tools import eq_

from auth.models import UserSync
from common import dbconfig


XML = """
<volunteers>
  <last_updated>20121202005516</last_updated>
  <current_volunteers>
    <volunteer>
      <name>
        <first>Ivan</first>
        <last>Krsti\xc4\x87</last>
        <nick>DJ Krsti\xc4\x87</nick>
      </name>
      <member_id>1</member_id>
      <email>person@chirpradio.org</email>
      <phone>
        <home></home>
        <cell></cell>
        <work></work>
      </phone>
      <avatar>http://volunteers.chirpradio.dev/_/i/volunteer_images/mikeg.jpeg</avatar>
      <urls>
        <twitter></twitter>
        <facebook></facebook>
        <website></website>
      </urls>
      <bio><![CDATA[
    (DJ bio text).]]></bio>
    </volunteer>
  </current_volunteers>
</volunteers>
"""


class TestSyncUsers(TestCase):

    def setUp(self):
        dbconfig['chirpradio.member_api.url'] = 'http://waaatjusttesting.com/api'
        dbconfig['chirpradio.member_api.user'] = 'example_user'
        dbconfig['chirpradio.member_api.password'] = 'example_pw'
        self.url = reverse('auth.cron.sync_users')

    def tearDown(self):
        for ob in UserSync.all():
            ob.delete()

    @fudge.patch('auth.cron.urlfetch.fetch')
    @fudge.patch('auth.cron.taskqueue')
    def test_sync(self, fetch, tq):
        (fetch.expects_call().returns_fake()
                             .has_attr(status_code=200,
                                       content=XML))

        def user_data(data):
            user = json.loads(data['user'])
            eq_(user['name_first'], 'Ivan')
            eq_(user['name_last'], u'Krsti\u0107')
            eq_(user['member_id'], 1)
            eq_(user['nick'], u'DJ Krsti\u0107')
            eq_(user['email'], 'person@chirpradio.org')
            return True

        (tq.expects('add')
           .with_args(
               url=reverse('auth.tasks.sync_user'),
               params=arg.passes_test(user_data),
           ))

        res = self.client.post(self.url,
                               HTTP_X_APPENGINE_CRON='true')
        eq_(res.status_code, 200)
        eq_(UserSync.all()[0].last_sync.timetuple()[0:3],
            date(2012, 12, 2).timetuple()[0:3])

    @fudge.patch('auth.cron.urlfetch.fetch')
    @fudge.patch('auth.cron.taskqueue')
    def test_no_need_for_sync(self, fetch, tq):
        (fetch.expects_call().returns_fake()
                             .has_attr(status_code=200,
                                       content=XML))
        sync = UserSync()
        sync.last_sync = datetime(2012, 12, 2, 0, 55, 16)  # last sync exact
        sync.put()

        self.client.post(self.url, HTTP_X_APPENGINE_CRON='true')

    @fudge.patch('auth.cron.urlfetch.fetch')
    @fudge.patch('auth.cron.taskqueue')
    def test_deactivate(self, fetch, tq):
        suspended = dedent("""\
            <volunteers>
              <last_updated>20121202005516</last_updated>
              <suspended_volunteers>
                <volunteer>
                  <name>
                    <first>Ivan</first>
                    <last>Krsti\xc4\x87</last>
                    <nick>DJ Krsti\xc4\x87</nick>
                  </name>
                  <member_id>1</member_id>
                  <email>person@chirpradio.org</email>
                </volunteer>
              </suspended_volunteers>
            </volunteers>
            """)
        (fetch.expects_call().returns_fake()
                             .has_attr(status_code=200,
                                       content=suspended))
        (tq.expects('add')
           .with_args(
               url=reverse('auth.tasks.deactivate_user'),
               params={'external_id': '1'},
           ))

        self.client.post(self.url, HTTP_X_APPENGINE_CRON='true')
