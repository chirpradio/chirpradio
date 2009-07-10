
from django.test import TestCase
from django.core.urlresolvers import reverse
import datetime
import unittest
from auth import roles
from auth.models import User
from playlists.models import Playlist, PlaylistTrack

__all__ = ['TestPlaylistViews']

class TestPlaylistViews(TestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
    
    def tearDown(self):
        for pl in Playlist.all():
            for track in PlaylistTrack.all().filter('playlist=', pl):
                track.delete()
            pl.delete()
    
    def test_view_shows_3_hours_of_tracks(self):
        dj_user = User.all().filter('email =', 'test@test.com')[0]
        playlist = Playlist(dj_user=dj_user, playlist_type='on-air')
        playlist.put()
        track = PlaylistTrack(
                    playlist=playlist, 
                    freeform_artist_name="Steely Dan",
                    freeform_album_title="Aja",
                    freeform_track_title="Peg")
        track.put()
        track = PlaylistTrack(
                    playlist=playlist, 
                    freeform_artist_name="Def Leoppard",
                    freeform_album_title="Pyromania",
                    freeform_track_title="Photograph")
        track.put()
        track = PlaylistTrack(
                    playlist=playlist, 
                    freeform_artist_name="Freestyle Fellowship",
                    freeform_album_title="To Whom It May Concern",
                    freeform_track_title="Five O'Clock Follies")
        # older than 3 hours:
        track.established = datetime.datetime.now() - datetime.timedelta(hours=3, minutes=2)
        track.put()
        
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].track_title, "Photograph")
        self.assertEquals(tracks[1].track_title, "Peg")
        self.assertEquals(len(tracks), 2, "tracks older than 3 hours were not hidden")
    
    def test_add_track_with_minimal_fields(self):
        resp = self.client.post(reverse('playlists_add_track'), {
            'artist': "Squarepusher",
            'song_title': "Port Rhombus"
        })
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")
    
    def test_add_track_with_all_fields(self):
        resp = self.client.post(reverse('playlists_add_track'), {
            'artist': "Squarepusher",
            'song_title': "Port Rhombus",
            "album": "Port Rhombus EP",
            "label": "Warp Records",
            "song_notes": "Dark melody. Really nice break down into half time."
        })
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")
        self.assertEquals(tracks[0].album_title, "Port Rhombus EP")
        self.assertEquals(tracks[0].label, "Warp Records")
        self.assertEquals(tracks[0].notes, 
                "Dark melody. Really nice break down into half time.")

    def test_unicode_track_entry(self):
        resp = self.client.post(reverse('playlists_add_track'), {
            'artist': u'Ivan Krsti\u0107',
            'song_title': u'Ivan Krsti\u0107',
            "album": u'Ivan Krsti\u0107',
            "label": u'Ivan Krsti\u0107',
            "song_notes": u'Ivan Krsti\u0107'
        })
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].track_title, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].album_title, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].label, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].notes, u'Ivan Krsti\u0107')
