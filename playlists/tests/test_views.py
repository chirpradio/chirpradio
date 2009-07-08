
from django.test import TestCase
from django.core.urlresolvers import reverse
import datetime
import unittest
from auth import roles
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
    
    def test_add_track_with_minimal_fields(self):
        resp = self.client.post(reverse('playlists_add_track'), {
            'artist': "Squarepusher",
            'song_title': "Port Rhombus"
        })
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context
        tracks = [t for t in context['tracks']]
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
        tracks = [t for t in context['tracks']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")
        self.assertEquals(tracks[0].album_title, "Port Rhombus EP")
        self.assertEquals(tracks[0].label, "Warp Records")
        self.assertEquals(tracks[0].notes, 
                "Dark melody. Really nice break down into half time.")

