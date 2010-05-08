
###
### Copyright 2010 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the 'License');
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an 'AS IS' BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

from __future__ import with_statement

from unittest import TestCase

from django.utils import simplejson
from django.test import TestCase as DjangoTestCase
import django.test.client
from django.core.urlresolvers import reverse
from django.conf import settings
import fudge
from fudge.inspector import arg

from auth import roles
import errors.middleware

class ClientHandlerWithErroHandler(django.test.client.ClientHandler):
    
    def load_middleware(self):
        from django.conf import settings
        
        middleware = [n for n in settings.MIDDLEWARE_CLASSES]
        if 'errors.middleware.GoogleAppEngineErrorMiddleware' not in middleware:
            # e.g. in case this middleware was excluded during debug mode
            middleware.append('errors.middleware.GoogleAppEngineErrorMiddleware')
        settings.MIDDLEWARE_CLASSES = middleware
        
        super(ClientHandlerWithErroHandler, self).load_middleware()

class TestErrorHandler(DjangoTestCase):
    
    def setUp(self):
        self.orig_middleware = [m for m in settings.MIDDLEWARE_CLASSES]
        self.client.handler = ClientHandlerWithErroHandler() # custom handler with middleware applied
        self.client.login(email="test@test.com", roles=[roles.DJ])
        
    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.orig_middleware
        fudge.clear_expectations()
    
    @fudge.with_fakes
    def test_unexpected_error_is_logged(self):
        fake_logging = fudge.Fake('logging').expects('exception')
        with fudge.patched_context(errors.middleware, "logging", fake_logging):   
            response = self.client.get(reverse('errors._test_errorhandler'))
        
        self.assertEqual(response.context['readable_exception'], 'RuntimeError')
    
    @fudge.with_fakes
    def test_expected_error_is_logged(self):
        fake_logging = fudge.Fake('logging').expects('exception')
        with fudge.patched_context(errors.middleware, "logging", fake_logging):   
            response = self.client.get(reverse('errors._test_errorhandler'), {
                'type': '0' # first catchable exception
            })
            
        self.assertEqual(response.context['readable_exception'], 'datastore_errors.Timeout')

