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

import unittest

from django import http
from django.test.client import Client

from google.appengine.ext import db

from djdb import models


class ViewsTestCase(unittest.TestCase):

    def test_landing_page(self):
        client = Client()
        client.login(email="test@test.com")

        response = client.get("/djdb/")
        self.assertEqual(200, response.status_code)

    def test_image_serving(self):
        img = models.DjDbImage(image_data="test data",
                               image_mimetype="image/jpeg",
                               sha1="test_sha1")
        img.save()

        client = Client()
        client.login(email='test@test.com')

        response = client.get(img.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual('test data', response.content)
        self.assertEqual("image/jpeg", response['Content-Type'])

        # Check that we 404 on a bad SHA1.
        response = client.get(img.url + 'trailing garbage')
        self.assertEqual(404, response.status_code)
