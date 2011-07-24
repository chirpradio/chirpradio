from __future__ import with_statement

from django.test import TestCase, Client

from nose.tools import eq_

from landing_page import views as lp_views


class TestGoMobile(TestCase):

    def get(self, user_agent=None):
        kw = {}
        if user_agent:
            kw['HTTP_USER_AGENT'] = user_agent
        return self.client.get('/m', **kw)

    def test_iphone(self):
        rs = self.get('Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_1_2 '
                      'like Mac OS X; en-us) AppleWebKit/528.18 '
                      '(KHTML, like Gecko) Version/4.0 Mobile/7D11 '
                      'Safari/528.16')
        eq_(rs['LOCATION'], lp_views.mobile_app_urls['iphone'])

    def test_android(self):
        rs = self.get('Mozilla/5.0 (Linux; U; Android 2.2; en-us; '
                      'Nexus One Build/FRF91) AppleWebKit/533.1 '
                      '(KHTML, like Gecko) Version/4.0 Mobile Safari/533.1')
        eq_(rs['LOCATION'], lp_views.mobile_app_urls['android'])

    def test_blackberry(self):
        rs = self.get('Mozilla/5.0 (BlackBerry; U; BlackBerry 9800; en) '
                      'AppleWebKit/534.1+ (KHTML, Like Gecko) '
                      'Version/6.0.0.141 Mobile Safari/534.1+')
        eq_(rs['LOCATION'], lp_views.mobile_app_urls['blackberry'])

    def test_unknown(self):
        rs = self.get('Mozilla/5.0 UNKNOWN')
        eq_(rs['LOCATION'], lp_views.mobile_app_urls['__default__'])

    def test_missing_agent(self):
        rs = self.get()
        eq_(rs['LOCATION'], lp_views.mobile_app_urls['__default__'])
