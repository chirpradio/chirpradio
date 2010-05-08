
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
import fudge
from fudge.inspector import arg
from django.core.urlresolvers import reverse

from auth import roles
import errors.middleware

class ClientHandlerWithErroHandler(django.test.client.ClientHandler):
    
    def load_middleware(self):
        from django.conf import settings
        
        m = [n for n in settings.MIDDLEWARE_CLASSES]
        if 'errors.middleware.GoogleAppEngineErrorMiddleware' not in m:
            # e.g. in case this middleware was excluded while in debug mode
            m.append('errors.middleware.GoogleAppEngineErrorMiddleware')
        settings.MIDDLEWARE_CLASSES = m
        
        super(ClientHandlerWithErroHandler, self).load_middleware()

class TestErrorHandler(DjangoTestCase):
    
    def setUp(self):
        self.client.handler = ClientHandlerWithErroHandler() # custom handler with middleware applied
        self.client.login(email="test@test.com", roles=[roles.DJ])
        
    def tearDown(self):
        fudge.clear_expectations()
    
    @fudge.with_fakes
    def test_unexpected_error_is_logged(self):
        fake_logging = fudge.Fake('logging').expects('exception')
        with fudge.patched_context(errors.middleware, "logging", fake_logging):   
            try:
                self.client.get(reverse('errors._test_errorhandler'))
            except RuntimeError:
                pass

