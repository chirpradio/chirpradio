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

import auth
from django.test import TestCase
from django.core.urlresolvers import reverse
import datetime
import unittest
from auth import roles
from auth.models import User
from playlists.models import Playlist, PlaylistTrack, PlaylistBreak, ChirpBroadcast
from djdb.models import Artist, Album, Track

__all__ = ['TestPlaylistViews', 'TestPlaylistViewsWithLibrary', 
           'TestDeleteTrackFromPlaylist']

class PlaylistViewsTest(TestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
    
    def tearDown(self):
        for pl in Playlist.all():
            for track in PlaylistTrack.all().filter('playlist =', pl):
                track.delete()
            pl.delete()

    def assertNoFormErrors(self, response):
        if response.context and response.context[0].get('form'):
            self.assertEquals(response.context[0]['form'].errors.as_text(), "")
    
    def get_selector(self):
        return User.all().filter('email =', 'test@test.com')[0]

class TestPlaylistViews(PlaylistViewsTest):
    
    def test_view_shows_3_hours_of_tracks(self):
        selector = self.get_selector()
        playlist = ChirpBroadcast()
        track = PlaylistTrack(
                    playlist=playlist, 
                    selector=selector,
                    freeform_artist_name="Steely Dan",
                    freeform_album_title="Aja",
                    freeform_track_title="Peg")
        track.put()
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector, 
                    freeform_artist_name="Def Leoppard",
                    freeform_album_title="Pyromania",
                    freeform_track_title="Photograph")
        track.put()
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector, 
                    freeform_artist_name="Freestyle Fellowship",
                    freeform_album_title="To Whom It May Concern",
                    freeform_track_title="Five O'Clock Follies")
        # older than 3 hours:
        track.established = datetime.datetime.now() - datetime.timedelta(hours=3, minutes=2)
        track.put()
        
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].track_title, "Photograph")
        self.assertEquals(tracks[1].track_title, "Peg")
        self.assertEquals(len(tracks), 2, "tracks older than 3 hours were not hidden")
    
    def test_add_track_with_minimal_fields(self):
        resp = self.client.post(reverse('playlists_add_event'), {
            'artist': "Squarepusher",
            'song': "Port Rhombus"
        })
        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")
        
        # when this user has created the entry she gets a link to delete it
        assert '[delete]' in resp.content
    
    def test_add_track_with_all_fields(self):
        resp = self.client.post(reverse('playlists_add_event'), {
            'artist': "Squarepusher",
            'song': "Port Rhombus",
            "album": "Port Rhombus EP",
            "label": "Warp Records",
            "song_notes": "Dark melody. Really nice break down into half time."
        })
        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")
        self.assertEquals(tracks[0].album_title, "Port Rhombus EP")
        self.assertEquals(tracks[0].label, "Warp Records")
        self.assertEquals(tracks[0].notes, 
                "Dark melody. Really nice break down into half time.")
    
    def test_add_tracks_to_existing_stream(self):
        # add several tracks:
        resp = self.client.post(reverse('playlists_add_event'), {
            'artist': "Steely Dan",
            'song': "Peg",
        })
        self.assertNoFormErrors(resp)
        resp = self.client.post(reverse('playlists_add_event'), {
            'artist': "Hall & Oates",
            'song': "M.E.T.H.O.D. of Love",
        })
        self.assertNoFormErrors(resp)
        
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Hall & Oates")
        self.assertEquals(tracks[1].artist_name, "Steely Dan")

    def test_unicode_track_entry(self):
        resp = self.client.post(reverse('playlists_add_event'), {
            'artist': u'Ivan Krsti\u0107',
            'song': u'Ivan Krsti\u0107',
            "album": u'Ivan Krsti\u0107',
            "label": u'Ivan Krsti\u0107',
            "song_notes": u'Ivan Krsti\u0107'
        })
        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].track_title, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].album_title, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].label, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].notes, u'Ivan Krsti\u0107')
    
    def test_add_break(self):
        playlist = ChirpBroadcast()
        selector = self.get_selector()
        track = PlaylistTrack(
                    playlist=playlist, 
                    selector=selector,
                    freeform_artist_name="Steely Dan",
                    freeform_album_title="Aja",
                    freeform_track_title="Peg")
        track.put()
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector, 
                    freeform_artist_name="Def Leoppard",
                    freeform_album_title="Pyromania",
                    freeform_track_title="Photograph")
        track.put()
        
        # add the break:
        resp = self.client.post(reverse('playlists_add_event'), {
            'submit': "Add Break"
        })
        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        
        # add one track after the break:
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector, 
                    freeform_artist_name="Kid Sister",
                    freeform_album_title="Ultraviolet",
                    freeform_track_title="Right Hand Hi")
        track.put()
        
        resp = self.client.get(reverse('playlists_landing_page'))
        
        context = resp.context[0]
        events = [t for t in context['playlist_events']]
        
        self.assertEqual(events[0].artist_name, "Kid Sister")
        self.assertEqual(events[0].is_break, False)
        self.assertEqual(events[0].is_new, True)
        
        self.assertEqual(events[1].is_break, True)
        self.assertEqual(events[1].is_new, False)
        
        self.assertEqual(events[2].artist_name, "Def Leoppard")
        self.assertEqual(events[2].is_break, False)
        self.assertEqual(events[2].is_new, False)
        
        self.assertEqual(events[3].artist_name, "Steely Dan")
        self.assertEqual(events[3].is_break, False)
        self.assertEqual(events[3].is_new, False)
        
        # print resp.content
        assert '<p class="break">Break</p>' in resp.content
        assert '<p><span class="artist">Def Leoppard</span>' in resp.content
        assert '<p><span class="artist">Steely Dan</span>' in resp.content

class TestPlaylistViewsWithLibrary(PlaylistViewsTest):
    
    def setUp(self):
        super(TestPlaylistViewsWithLibrary, self).setUp()
                
        # some data to work with:
        self.stevie = Artist.create(name="Stevie Wonder")
        self.stevie.put()
        self.talking_book = Album(
            album_id=1, # faux
            artist=self.stevie, 
            title="Talking Book",
            import_timestamp=datetime.datetime.now(),
            num_tracks=10)
        self.talking_book.put()
        self.tracks = {}
        for idx, title in enumerate([
                'You Are The Sunshine Of My Life',
                'Maybe Your Baby',
                'You And I (We Can Conquer The World)'
                # ...etc...
                ]):
            track = Track(
                        album=self.talking_book,
                        title=title,
                        sampling_rate_hz=44000,
                        bit_rate_kbps=256,
                        channels='stereo',
                        duration_ms=60*60*3, # faux
                        track_num=idx+1)
            self.tracks[title] = track
            track.put()
    
    def tearDown(self):
        for model in (
                PlaylistTrack, Playlist, User,
                Album, Artist, Track ):
            for obj in model.all():
                obj.delete()
    
    def test_add_track_linked_to_library(self):
        stevie = Artist.all().filter("name =", "Stevie Wonder")[0]
        talking_book = Album.all().filter("title =", "Talking Book")[0]
        sunshine = Track.all().filter("title =", "You Are The Sunshine Of My Life")[0]
        resp = self.client.post(reverse('playlists_add_event'), {
            'artist_key': stevie.key(),
            'artist': stevie.name,
            'song': "You Are The Sunshine Of My Life",
            'song_key': sunshine.key(),
            'album_key': talking_book.key(),
            'album': talking_book.title
        })
        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Stevie Wonder")
        self.assertEquals(tracks[0].artist.key(), stevie.key())
        self.assertEquals(tracks[0].album_title, "Talking Book")
        self.assertEquals(tracks[0].album.key(), talking_book.key())
        self.assertEquals(tracks[0].track_title, "You Are The Sunshine Of My Life")
        self.assertEquals(tracks[0].track.key(), sunshine.key())

class TestDeleteTrackFromPlaylist(PlaylistViewsTest):
    
    def setUp(self):
        super(TestDeleteTrackFromPlaylist, self).setUp()
        self.playlist = ChirpBroadcast()
        selector = self.get_selector()
        self.track = PlaylistTrack(
                    playlist=self.playlist, 
                    selector=selector,
                    freeform_artist_name="Steely Dan",
                    freeform_album_title="Aja",
                    freeform_track_title="Peg")
        self.track.put()
    
    def test_delete_known_track(self):
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Steely Dan")
        
        resp = self.client.get(reverse('playlists_delete_event', 
                                        args=[self.track.key()]))
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks, [])
    
    def test_delete_unknown_track(self):
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Steely Dan")

        resp = self.client.get(reverse('playlists_delete_event', 
                                        args=['<bogus-key>']))
        
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        
        # should be no change:
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Steely Dan")
    
    def test_cannot_delete_someone_elses_track(self):
        other_user = User(email="other@elsewhere.com")
        other_user.roles.append(auth.roles.DJ)
        other_user.put()
        other_track = PlaylistTrack(
                    playlist=self.playlist, 
                    selector=other_user,
                    freeform_artist_name="Peaches",
                    freeform_track_title="Rock Show")
        other_track.put()
        
        resp = self.client.get(reverse('playlists_delete_event', 
                                        args=[other_track.key()]))

        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        
        # should be no change:
        context = resp.context[0]
        tracks = [t.artist_name for t in context['playlist_events']]
        self.assertEquals(tracks, ["Peaches", "Steely Dan"])
    
    def test_delete_link_appears_for_current_user(self):
        resp = self.client.get(reverse('playlists_landing_page'))
        assert '[delete]' in resp.content
        
        for track in PlaylistTrack.all():
            track.delete()
        
        other_user = User(email="other@elsewhere.com")
        other_user.roles.append(auth.roles.DJ)
        other_user.put()
        other_track = PlaylistTrack(
                    playlist=self.playlist, 
                    selector=other_user,
                    freeform_artist_name="Peaches",
                    freeform_track_title="Rock Show")
        other_track.put()
        
        resp = self.client.get(reverse('playlists_landing_page'))
        assert '[delete]' not in resp.content
