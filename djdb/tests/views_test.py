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
from django.test import TestCase
from django import http
from django.test.client import Client
from google.appengine.ext import db
from djdb import models
from djdb import search
from auth import roles

class ViewsTestCase(TestCase):
    def setUp(self):
        # Log in.
        self.client.login(email="test@test.com")

        # Create an image entry.
        self.img = models.DjDbImage(image_data="test data",
                                    image_mimetype="image/jpeg",
                                    sha1="test_sha1")
        self.img.save()
        
    def tearDown(self):
        self.img.delete()

    def test_landing_page(self):
        response = self.client.get("/djdb/")
        self.assertEqual(200, response.status_code)

    def test_image_serving(self):
        response = self.client.get(self.img.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual('test data', response.content)
        self.assertEqual("image/jpeg", response['Content-Type'])

        # Check that we 404 on a bad SHA1.
        response = self.client.get(self.img.url + 'trailing garbage')
        self.assertEqual(404, response.status_code)

class AutocompleteViewsTestCase(TestCase):
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
        
        idx = search.Indexer()
        
        # Create some test artists.
        art1 = models.Artist(name=u"Fall, The", parent=idx.transaction,
                             key_name="art1")
        self.the_fall = art1
        art2 = models.Artist(name=u"Eno, Brian", parent=idx.transaction,
                             key_name="art2")
        self.eno = art2
        
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
        
        for i, track_title in enumerate((u"Spider And I", 
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
    
    def test_track_full_name_by_artist(self):
        response = self.client.get("/djdb/track/search.txt", {
                                        'q':'spider and I',
                                        'artist_key': self.eno.key()})
                                        
        ent = models.Track.all().filter("title =", "Spider And I")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.title, ent.key()))
    
    def test_track_full_name_by_wrong_artist(self):
        response = self.client.get("/djdb/track/search.txt", {
                                        'q':'spider and I',
                                        'artist_key': self.the_fall.key()})
                                        
        self.assertEqual(response.content, "", 
            "Expected no results since Spider And I is not by The Fall, got: %r" % 
                                                                response.content)
    
    def test_track_partial_name(self):
        response = self.client.get("/djdb/track/search.txt", {'q':'spid'})
        ent = models.Track.all().filter("title =", "Spider And I")[0]
        self.assertEqual(response.content, "%s|%s\n" % (ent.title, ent.key()))
    
    def test_track_no_matches(self):
        # when there are no Track matches but there are Artist matches, 
        # the entity key does not get added to the matches dict
        response = self.client.get("/djdb/track/search.txt", {'q':'eno'})
        self.assertEqual(response.content, "")

class UpdateAlbumViewsTestCase(TestCase):
    def setUp(self):
        # Log in.
        self.client = Client()
        self.client.login(email='test@test.com', roles=[roles.DJ])
        
        # Get user.
        self.user = models.User.all().filter('email =', 'test@test.com')[0]
    
        # Create an artist.
        self.artist = models.Artist(name='Artist')
        self.artist.put()
        
        # Create an album.
        self.album = models.Album(title='Album',
                                  label='Label',
                                  year=2010,
                                  album_id=1,
                                  import_timestamp=datetime.datetime.now(),
                                  album_artist=self.artist,
                                  num_tracks=1)
        self.album.put()

    def test_update_album(self):
        vars = {'label': 'New Label',
                'year': 2009,
                'update': 'Update'}
        response = self.client.post('/djdb/album/%d/info' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        album = db.get(self.album.key())
        self.assertEqual(self.album.label, 'Label')
        self.assertEqual(self.album.year, 2010)

        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()
        vars = {'label': 'New Label',
                'year': 2009,
                'update': 'Update'}
        response = self.client.post('/djdb/album/%d/info' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        album = db.get(self.album.key())
        self.assertEqual(album.label, 'New Label')
        self.assertEqual(album.year, 2009)

class ReviewViewsTestCase(TestCase):
    def setUp(self):
        # Log in.
        self.client = Client()
        self.client.login(email='test@test.com', roles=[roles.DJ])
        
        # Get user.
        self.user = models.User.all().filter('email =', 'test@test.com')[0]
        
        # Create a review user.
        self.review_user = models.User(email='test_user@test.com',
                                       first_name='Test',
                                       last_name='User')
        self.review_user.put()
        
        # Create an artist.
        self.artist = models.Artist(name='Artist')
        self.artist.put()
        
        # Create an album.
        self.album = models.Album(title='Album',
                                  album_id=1,
                                  import_timestamp=datetime.datetime.now(),
                                  album_artist=self.artist,
                                  num_tracks=1)
        self.album.put()

    def test_new_review(self):
        # Test get - emty form.
        response = self.client.get('/djdb/album/%d/new_review' % self.album.album_id)
        self.assertEqual(response.status_code, 200)
        
        # Test save review with no user field.
        vars = {'save': 'Save',
                'text': 'Album review.',
                'author_key': self.user.key()}
        response = self.client.post('/djdb/album/%d/new_review' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.reviews[-1].text, 'Album review.')
        self.assertEqual(album.reviews[-1].author.key(), self.user.key())

        # Test save review with user field of existing user.
        vars = {'save': 'Save',
                'text': 'Album review.',
                'author': 'Test User'}
        response = self.client.post('/djdb/album/%d/new_review' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.reviews[-1].text, 'Album review.')
        self.assertEqual(album.reviews[-1].author.key(), self.review_user.key())

        # Test save review with user field of non-existing user.
        vars = {'save': 'Save',
                'text': 'Album review.',
                'author': 'Nonexisting User'}
        response = self.client.post('/djdb/album/%d/new_review' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.reviews[-1].text, 'Album review.')
        self.assertEqual(album.reviews[-1].author_name, "Nonexisting User")

    def test_edit_review(self):
        # Post a new review.
        vars = {'save': 'Save',
                'text': 'Album review.',
                'author_key': self.user.key()}
        self.client.post('/djdb/album/%d/new_review' % self.album.album_id, vars)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        doc_key = album.reviews[0].key()

        # Test get page.
        response = self.client.post('/djdb/album/%d/edit_review/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['review'].text, 'Album review.')
        
        # Test edit review with no user.
        vars = {'save': 'Save',
                'text': 'Edited album review 1.',
                'author_key': self.user.key()}
        response = self.client.post('/djdb/album/%d/edit_review/%s' % (self.album.album_id, doc_key), vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.reviews[0].text, 'Edited album review 1.')
        self.assertEqual(album.reviews[0].author.key(), self.user.key())

        # Test edit review with different user and key.
        vars = {'save': 'Save',
                'text': 'Edited album review 2.',
                'author': 'Test User',
                'author_key': self.review_user.key()}
        response = self.client.post('/djdb/album/%d/edit_review/%s' % (self.album.album_id, doc_key), vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.reviews[0].text, 'Edited album review 2.')
        self.assertEqual(album.reviews[0].author.key(), self.review_user.key())

        # Test edit review with different existing user but no key.
        vars = {'save': 'Save',
                'text': 'Edited album review 3.',
                'author': 'Test User'}
        response = self.client.post('/djdb/album/%d/edit_review/%s' % (self.album.album_id, doc_key), vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.reviews[0].text, 'Edited album review 3.')
        self.assertEqual(album.reviews[0].author.key(), self.review_user.key())

        # Test edit review with non-existing user.
        vars = {'save': 'Save',
                'text': 'Edited album review 4.',
                'author': 'Nonexisting User'}
        response = self.client.post('/djdb/album/%d/edit_review/%s' % (self.album.album_id, doc_key), vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.reviews[0].text, 'Edited album review 4.')
        self.assertEqual(album.reviews[0].author_name, 'Nonexisting User')
        
    def test_hide_unhide_review(self):
        # Post a new review.
        vars = {'save': 'Save',
                'text': 'Album review.',
                'author_key': self.user.key()}
        self.client.post('/djdb/album/%d/new_review' % self.album.album_id, vars)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        doc_key = album.reviews[0].key()

        # Test permissions.
        response = self.client.post('/djdb/album/%d/hide_review/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 403)

        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()

        # Test hide review.
        response = self.client.post('/djdb/album/%d/hide_review/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 200)
        doc = db.get(doc_key)
        self.assertEqual(doc.is_hidden, True)
        
        # Test unhide review.
        response = self.client.post('/djdb/album/%d/unhide_review/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 200)
        doc = db.get(doc_key)
        self.assertEqual(doc.is_hidden, False)

    def test_delete_review(self):
        # Post a new review.
        vars = {'save': 'Save',
                'text': 'Album review.',
                'author_key': self.user.key()}
        self.client.post('/djdb/album/%d/new_review' % self.album.album_id, vars)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        doc_key = album.reviews[0].key()

        # Test permissions.
        vars = {'doc_key': doc_key,
                'confirm': 'Confirm'}
        response = self.client.post('/djdb/album/%d/delete_review' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 403)

        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()

        # Test delete review.
        vars = {'review_key': doc_key,
                'confirm': 'Confirm'}
        response = self.client.post('/djdb/album/%d/delete_review' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        doc = db.get(doc_key)
        self.assertEqual(doc, None)
    
class CommentViewsTestCase(TestCase):
    def setUp(self):
        # Log in.
        self.client = Client()
        self.client.login(email='test@test.com', roles=[roles.DJ])
        
        # Get user.
        self.user = models.User.all().filter('email =', 'test@test.com')[0]
        
        # Create an artist.
        self.artist = models.Artist(name='Artist')
        self.artist.put()
        
        # Create an album.
        self.album = models.Album(title='Album',
                                  album_id=1,
                                  import_timestamp=datetime.datetime.now(),
                                  album_artist=self.artist,
                                  num_tracks=1)
        self.album.put()

#    def tearDown(self):
        # Delete test data.
#        self.album.delete()
#        self.artist.delete()
#        self.user.delete()

    def test_new_comment(self):
        # Test get - emty form.
        response = self.client.get('/djdb/album/%d/new_comment' % self.album.album_id)
        self.assertEqual(response.status_code, 200)
        
        # Test post - save comment.
        vars = {'save': 'Save',
                'text': 'Album comment.'}
        response = self.client.post('/djdb/album/%d/new_comment' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 302)
        
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.comments[0].text, 'Album comment.')

    def test_edit_comment(self):
        # Post a new comment.
        vars = {'save': 'Save',
                'text': 'Album comment.'}
        self.client.post('/djdb/album/%d/new_comment' % self.album.album_id, vars)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        doc_key = album.comments[0].key()

        # Test get - edit.
        response = self.client.post('/djdb/album/%d/edit_comment/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['comment'].text, 'Album comment.')
        
        # Test post - save comment.
        vars = {'save': 'Save',
                'text': 'Edited album comment.'}
        response = self.client.post('/djdb/album/%d/edit_comment/%s' % (self.album.album_id, doc_key), vars)
        self.assertEqual(response.status_code, 302)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        self.assertEqual(album.comments[0].text, 'Edited album comment.')

    def test_hide_unhide_comment(self):
        # Post a new comment.
        vars = {'save': 'Save',
                'text': 'Album comment.'}
        self.client.post('/djdb/album/%d/new_comment' % self.album.album_id, vars)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        doc_key = album.comments[0].key()

        # Test permissions.
        response = self.client.post('/djdb/album/%d/hide_comment/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 403)

        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()

        # Test hide comment.
        response = self.client.post('/djdb/album/%d/hide_comment/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 200)
        doc = db.get(doc_key)
        self.assertEqual(doc.is_hidden, True)
        
        # Test unhide comment.
        response = self.client.post('/djdb/album/%d/unhide_comment/%s' % (self.album.album_id, doc_key))
        self.assertEqual(response.status_code, 200)
        doc = db.get(doc_key)
        self.assertEqual(doc.is_hidden, False)

    def test_delete_comment(self):
        # Post a new comment.
        vars = {'save': 'Save',
                'text': 'Album comment.'}
        self.client.post('/djdb/album/%d/new_comment' % self.album.album_id, vars)
        album = models.Album.all().filter('album_id =', self.album.album_id).fetch(1)[0]
        doc_key = album.comments[0].key()

        # Test permissions.
        vars = {'doc_key': doc_key,
                'confirm': 'Confirm'}
        response = self.client.post('/djdb/album/%d/delete_comment' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 403)

        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()

        # Test delete comment.
        vars = {'comment_key': doc_key,
                'confirm': 'Confirm'}
        response = self.client.post('/djdb/album/%d/delete_comment' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        doc = db.get(doc_key)
        self.assertEqual(doc, None)

class  AlbumCategoryViewsTestCase(TestCase):
    def setUp(self):
        # Log in.
        self.client = Client()
        self.client.login(email='test@test.com', roles=[roles.DJ])

        # Get user.
        self.user = models.User.all().filter('email =', 'test@test.com')[0]
        
        # Create an artist.
        self.artist = models.Artist(name='Artist')
        self.artist.put()
        
        # Create some albums.
        for album_id, title in enumerate(['Album 1', 'Album 2', 'Album 3']):
            album = models.Album(title=title,
                                 album_id=album_id+1,
                                 import_timestamp=datetime.datetime.now(),
                                 album_artist=self.artist,
                                 num_tracks=1)
            album.put()

    def tearDown(self):
        # Remove test data.
        for album in self.artist.sorted_albums:
            album.delete()
        self.artist.delete()
        self.user.delete()
        
    def test_update_albums_forbidden(self):
        albums = self.artist.sorted_albums
        vars = {'checkbox_1': 'on',
                'checkbox_3': 'on',
                'album_key_1': albums[0].key(),
                'album_key_3': albums[2].key(),
                'mark_as': models.ALBUM_CATEGORIES[1]}
        response = self.client.post('/djdb/update_albums', vars)
        self.assertEqual(response.status_code, 403)
        
    def test_update_albums(self):
        self.user.roles.append(roles.MUSIC_DIRECTOR)
        self.user.save()
        
        albums = self.artist.sorted_albums
        vars = {'checkbox_1': 'on',
                'checkbox_3': 'on',
                'album_key_1': albums[0].key(),
                'album_key_3': albums[2].key(),
                'mark_as': models.ALBUM_CATEGORIES[1]}
        response = self.client.post('/djdb/update_albums', vars)
        self.assertEqual(response.status_code, 200)
        
        albums = self.artist.sorted_albums
        self.assertEqual(albums[0].category, models.ALBUM_CATEGORIES[1])
        self.assertEqual(albums[1].category, None)
        self.assertEqual(albums[2].category, models.ALBUM_CATEGORIES[1])

class TrackViewsTestCase(TestCase):
    def setUp(self):
        # Log in.
        self.client = Client()
        self.client.login(email='test@test.com', roles=[roles.DJ])

        # Get user.
        self.user = models.User.all().filter('email =', 'test@test.com')[0]

        # Create an artist.
        self.artist = models.Artist(name='Artist')
        self.artist.put()

        # Create an album.
        self.album = models.Album(title='Album',
                                  album_id=1,
                                  import_timestamp=datetime.datetime.now(),
                                  album_artist=self.artist,
                                  num_tracks=1)
        self.album.put()

        # Create some tracks.
        for track_num, title in enumerate(['Track 1', 'Track 2', 'Track 3', 'Track 4']):
            self.track = models.Track(album=self.album,
                                      title=title,
                                      track_num=track_num+1,
                                      sampling_rate_hz=44000,
                                      bit_rate_kbps=256,
                                      channels='stereo',
                                      duration_ms=60*60*3)
            self.track.put()

    def test_update_tracks_recommended(self):
        # Mark as recommended.
        vars = {'mark_as': 'recommended',
                'checkbox_1': 'on',
                'checkbox_3': 'on'}
        response = self.client.post('/djdb/album/%d/update_tracks' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        
        tracks = self.album.sorted_tracks
        self.assertEqual(tracks[0].current_tags[0], 'recommended')
        self.assertEqual(tracks[1].current_tags, [])
        self.assertEqual(tracks[2].current_tags[0], 'recommended')
        self.assertEqual(tracks[3].current_tags, [])

        # Unmark recommended.
        response = self.client.post('/djdb/album/%d/update_tracks' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        
        tracks = self.album.sorted_tracks
        self.assertEqual(tracks[0].current_tags, [])
        self.assertEqual(tracks[1].current_tags, [])
        self.assertEqual(tracks[2].current_tags, [])
        self.assertEqual(tracks[3].current_tags, [])

    def test_update_tracks_explicit(self):
        # Mark as explicit.
        vars = {'mark_as': 'explicit',
                'checkbox_2': 'on',
                'checkbox_4': 'on'}
        response = self.client.post('/djdb/album/%d/update_tracks' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        
        tracks = self.album.sorted_tracks
        self.assertEqual(tracks[0].current_tags, [])
        self.assertEqual(tracks[1].current_tags[0], 'explicit')
        self.assertEqual(tracks[2].current_tags, [])
        self.assertEqual(tracks[3].current_tags[0], 'explicit')

        # Unmark explicit.
        response = self.client.post('/djdb/album/%d/update_tracks' % self.album.album_id, vars)
        self.assertEqual(response.status_code, 200)
        
        tracks = self.album.sorted_tracks
        self.assertEqual(tracks[0].current_tags, [])
        self.assertEqual(tracks[1].current_tags, [])
        self.assertEqual(tracks[2].current_tags, [])
        self.assertEqual(tracks[3].current_tags, [])

class CrateViewsTestCase(TestCase):
    def setUp(self):
        # Log in.
        self.client = Client()
        self.client.login(email='test@test.com', roles=[roles.DJ])

        # Get user.
        self.user = models.User.all().filter('email =', 'test@test.com')[0]
        
        # Create a crate.
        self.crate = models.Crate(user=self.user)
        self.crate.put()
     
        # Create an artist.
        self.artist = models.Artist(name='Artist')
        self.artist.put()
        
        # Create an album.
        self.album = models.Album(title='Album',
                                  album_id=1,
                                  import_timestamp=datetime.datetime.now(),
                                  album_artist=self.artist,
                                  num_tracks=1)
        self.album.put()
                                  
        # Create a track.
        self.track = models.Track(album=self.album,
                                  title='Track',
                                  track_num=1,
                                  sampling_rate_hz=44000,
                                  bit_rate_kbps=256,
                                  channels='stereo',
                                  duration_ms=60*60*3)
        self.track.put()
        
    def tearDown(self):
        # Remove test data.
        self.crate.delete()
        self.track.delete()
        self.album.delete()
        self.artist.delete()
        self.user.delete()
         
    def test_crate_page(self):
        response = self.client.get('/djdb/crate')
        self.assertEqual(response.status_code, 200)
        
    def _add_crate_items(self):
        vars = {'artist':'Artist',
                'album': 'Album',
                'track': 'Track',
                'label': 'Label',
                'notes': 'Notes'}
        response = self.client.post('/djdb/crate/add_item', vars)
        self.assertEqual(response.status_code, 200)
        
        # Test get (adding existing artist, album, and track).
        vars = {'item_key': self.artist.key()}
        response = self.client.get('/djdb/crate/add_item', vars)
        self.assertEqual(response.status_code, 200)

        vars = {'item_key': self.album.key()}
        response = self.client.get('/djdb/crate/add_item', vars)
        self.assertEqual(response.status_code, 200)

        vars = {'item_key': self.track.key()}
        response = self.client.get('/djdb/crate/add_item', vars)
        self.assertEqual(response.status_code, 200)

    def test_crate_add_items(self):
        self._add_crate_items()
        crate = models.Crate.all().filter("user =", self.user).fetch(1)[0]
        crate_item = db.get(crate.items[0])
        self.assertEqual(crate_item.artist, 'Artist')
        self.assertEqual(crate_item.album, 'Album')
        self.assertEqual(crate_item.track, 'Track')
        self.assertEqual(crate_item.label, 'Label')
        self.assertEqual(crate_item.notes, 'Notes')
        
        self.assertEqual(crate.items[1], self.artist.key())
        self.assertEqual(crate.items[2], self.album.key())
        self.assertEqual(crate.items[3], self.track.key())
        
        self.assertEqual(crate.order, [1, 2, 3, 4])

    def test_crate_reorder(self):
        self._add_crate_items()
        vars = {'item[]': [4, 1, 2, 3]}
        response = self.client.get('/djdb/crate/reorder', vars)
        self.assertEqual(response.status_code, 200)
        
        crate = models.Crate.all().filter("user =", self.user).fetch(1)[0]
        self.assertEqual(crate.order, [4, 1, 2, 3])

        response = self.client.get('/djdb/crate')
        crate = models.Crate.all().filter("user =", self.user).fetch(1)[0]
        self.assertEqual(crate.items[0], self.track.key())
        self.assertEqual(crate.items[1].kind(), 'CrateItem')
        self.assertEqual(crate.items[2], self.artist.key())
        self.assertEqual(crate.items[3], self.album.key())
        self.assertEqual(crate.order, [1, 2, 3, 4])
        
    def test_crate_remove_item(self):
        self._add_crate_items()
        vars = {'item_key': self.album.key()}
        response = self.client.get('/djdb/crate/remove_item', vars)
        self.assertEqual(response.status_code, 200)
        
        crate = models.Crate.all().filter("user =", self.user).fetch(1)[0]
        self.assertEqual(crate.items[0].kind(), 'CrateItem')
        self.assertEqual(crate.items[1], self.artist.key())
        self.assertEqual(crate.items[2], self.track.key())
        self.assertEqual(crate.order, [1, 2, 3])
