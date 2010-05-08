
###
### Copyright 2009 The Chicago Independent Radio Project
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

__all__ = ['TestJSONHandler', 'TestAsEncodedString']

from unittest import TestCase

from django.utils import simplejson
from django.test import TestCase as DjangoTestCase

from auth import roles
from common import utilities

class TestJSONHandler(DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
    
    def test_json_error(self):
        response = self.client.get('/common/_make_json_error')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['content-type'], 'application/json')
        json_response = simplejson.loads(response.content)
        self.assertEqual(json_response['success'], False)
        self.assertEqual(json_response['error'], 
            "RuntimeError('When the moon shines on the 5th house on the 7th hour, "
                                                    "your shoe laces will unravel.',)")
        assert json_response['traceback'].startswith(
            "Traceback (most recent call last)"
        )
        assert json_response['traceback'].endswith(
            "RuntimeError: When the moon shines on the 5th house on the 7th hour, "
            "your shoe laces will unravel.\n"
        )

class TestAsEncodedString(TestCase):
    
    def test_encode_unicode(self):
        self.assertEqual(utilities.as_encoded_str(u'Ivan Krsti\u0107'), 
                            'Ivan Krsti\xc4\x87')
        self.assertEqual(utilities.as_encoded_str(u'Ivan Krsti\u0107', encoding='utf-16'), 
                            '\xff\xfeI\x00v\x00a\x00n\x00 \x00K\x00r\x00s\x00t\x00i\x00\x07\x01')
    
    def test_passthru_encoded_str(self):
        self.assertEqual(utilities.as_encoded_str('Ivan Krsti\xc4\x87'), 'Ivan Krsti\xc4\x87')
        

