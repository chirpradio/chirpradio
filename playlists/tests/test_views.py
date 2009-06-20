
from django.test import TestCase
from django.core.urlresolvers import reverse
import datetime
import unittest
from auth import roles

__all__ = ['TestPlaylistViews']

class TestPlaylistViews(TestCase):
    
    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
    
    def test_add_track(self):
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