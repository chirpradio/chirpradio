
from django.http import HttpRequest
from django.test import TestCase as DjangoTestCase
from django.template import RequestContext

class TestBaseContext(DjangoTestCase):
    
    def test_logout_url_redirects_to_current_page(self):
        request = HttpRequest()
        request.method = "GET"
        request.path = "/elsewhere/in/site"
        request.user = None
        ctx = RequestContext(request)
        self.assertEqual(ctx['logout_url'], '/auth/goodbye/?redirect=/elsewhere/in/site')