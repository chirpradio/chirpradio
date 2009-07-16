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

import datetime
import unittest
from django.test import TestCase as DjangoTestCase

from django import http
from django.test.client import Client

from google.appengine.ext import db

from djdb import models
from djdb import search
from auth import roles


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

class AutocompleteViewsTestCase(DjangoTestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
        
        idx = search.Indexer()
        
        # Create some test artists.
        art1 = models.Artist(name=u"Fall, The", parent=idx.transaction,
                             key_name="art1")
        art2 = models.Artist(name=u"Eno, Brian", parent=idx.transaction,
                             key_name="art2")
        # Create some test albums.
        alb1 = models.Album(title=u"This Nation's Saving Grace",
                            album_id=12345,
                            import_timestamp=datetime.datetime.now(),
                            album_artist=art1,
                            num_tracks=123,
                            parent=idx.transaction)
        alb2 = models.Album(title=u"Another Green World",
                            album_id=67890,
                            import_timestamp=datetime.datetime.now(),
                            album_artist=art2,
                            num_tracks=456,
                            parent=idx.transaction)
        
        for i, track_title in enumerate((   u"Spider And I", 
                                            u"Running To Tie Your Shoes", 
                                            u"Kings Lead Hat")):
            idx.add_track(models.Track(ufid="test3-%d" % i,
                                     album=alb2,
                                     sampling_rate_hz=44110,
                                     bit_rate_kbps=128,
                                     channels="mono",
                                     duration_ms=789,
                                     title=track_title,
                                     track_artist=art2,
                                     track_num=i+1,
                                     parent=idx.transaction))
        
        idx.add_artist(art1)
        idx.add_artist(art2)
        idx.add_album(alb1)
        idx.add_album(alb2)
        
        idx.save() # this also saves all objects
        
    def test_short_query_is_ignored(self):
        response = self.client.get("/djdb/artist/search.txt", {'q':'en'}) # too short
        self.assertEqual(response.content, "")
    
    def test_artist_full_name(self):
        response = self.client.get("/djdb/artist/search.txt", {'q':'brian eno'})
        ent = models.Artist.all().filter("name =", "Eno, Brian")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.pretty_name, ent.key()))
    
    def test_artist_partial_name(self):
        response = self.client.get("/djdb/artist/search.txt", {'q':'fal'}) # The Fall
        ent = models.Artist.all().filter("name =", "Fall, The")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.pretty_name, ent.key()))
    
    def test_album_full_name(self):
        response = self.client.get("/djdb/album/search.txt", {'q':'another green world'})
        ent = models.Album.all().filter("title =", "Another Green World")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.title, ent.key()))
    
    def test_album_partial_name(self):
        response = self.client.get("/djdb/album/search.txt", {'q':'another'})
        ent = models.Album.all().filter("title =", "Another Green World")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.title, ent.key()))
    
    def test_track_full_name(self):
        response = self.client.get("/djdb/track/search.txt", {'q':'spider and I'})
        ent = models.Track.all().filter("title =", "Spider And I")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.title, ent.key()))
    
    def test_track_partial_name(self):
        response = self.client.get("/djdb/track/search.txt", {'q':'spid'})
        ent = models.Track.all().filter("title =", "Spider And I")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.title, ent.key()))


