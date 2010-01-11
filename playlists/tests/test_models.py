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
from djdb.models import Artist, Album, Track
from playlists.models import (
        Playlist, DJPlaylist, BroadcastPlaylist, PlaylistTrack, 
        PlaylistBreak, ChirpBroadcast)
import auth.roles
from auth.models import User
from google.appengine.api.datastore_errors import BadValueError
import time

__all__ = ['TestPlaylist', 'TestPlaylistTrack', 'TestPlaylistBreak']

def create_dj():    
    dj = User(email="test")
    dj.roles.append(auth.roles.DJ)
    dj.put()
    return dj

class TestPlaylist(unittest.TestCase):
    
    def setUp(self):
        for obj in User.all():
            obj.delete()
    
    def test_non_dj_cannot_create_playlist(self):
        not_a_dj = User(email="test")
        not_a_dj.put()
        def make_playlist():
            playlist = DJPlaylist(name='funk 45 collection', created_by_dj=not_a_dj)
            playlist.put()
        self.assertRaises(ValueError, make_playlist)
    
    def test_dj_playlist_creation(self):
        dj = create_dj()
        playlist = DJPlaylist(name='Best of Celine Dion', created_by_dj=dj)
        playlist.put()
        self.assertEqual(playlist.track_count, 0)
        self.assertEqual(
            playlist.established.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])
        self.assertEqual(
            playlist.modified.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])
            
        # just for sanity, not very good tests:
        self.assertEqual(
            playlist.established_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])
        self.assertEqual(
            playlist.modified_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])

    def test_chirp_broadcast_playlist_is_a_singleton(self):
        first = ChirpBroadcast()
        second = ChirpBroadcast()
        self.assertEqual(first.key(), second.key())
        fetched = BroadcastPlaylist.all().filter("channel =", "CHIRP")[0]
        self.assertEqual(fetched.key(), first.key())
    
    def test_chirp_broadcast_playlist(self):
        playlist = ChirpBroadcast()
        self.assertEqual(
            playlist.established.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])
        self.assertEqual(
            playlist.modified.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])
            
        # just for sanity, not very good tests:
        self.assertEqual(
            playlist.established_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])
        self.assertEqual(
            playlist.modified_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])

class PlaylistEventTest(unittest.TestCase):
    
    def setUp(self):
        for model in (
                PlaylistTrack, Playlist, User,
                Album, Artist, Track ):
            for obj in model.all():
                obj.delete()
                
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

class TestPlaylistTrack(PlaylistEventTest):
    
    def test_track_missing_title_raises_error(self):
        selector = create_dj()
        def make_track():
            playlist = ChirpBroadcast()
            track = PlaylistTrack(
                selector=selector,
                playlist=playlist,
                artist=self.stevie,
                album=self.talking_book
            )
            track.put()
        self.assertRaises(ValueError, make_track)
    
    def test_track_missing_artist_raises_error(self):
        selector = create_dj()
        def make_track():
            playlist = ChirpBroadcast()
            track = PlaylistTrack(
                selector=selector,
                playlist=playlist,
                album=self.talking_book,
                track=self.tracks['You Are The Sunshine Of My Life']
            )
            track.put()
        self.assertRaises(ValueError, make_track)
    
    def test_track_by_references(self):
        selector = create_dj()
        playlist = ChirpBroadcast()
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            artist=self.stevie,
            album=self.talking_book,
            track=self.tracks['You Are The Sunshine Of My Life']
        )
        track.put()
        self.assertEqual(track.artist_name, "Stevie Wonder")
        self.assertEqual(track.artist, self.stevie)
        self.assertEqual(track.album_title, "Talking Book")
        self.assertEqual(track.album, self.talking_book)
        self.assertEqual(track.track_title, "You Are The Sunshine Of My Life")
        self.assertEqual(track.track, self.tracks['You Are The Sunshine Of My Life'])
    
    def test_track_by_free_entry(self):
        selector = create_dj()
        playlist = ChirpBroadcast()
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="Stevie Wonder",
            freeform_album_title="Talking Book",
            freeform_track_title='You Are The Sunshine Of My Life',
            freeform_label='Warner Bros.',
            notes="This track is a bit played out but it still has some nice melodies"
        )
        track.put()
        self.assertEqual(track.artist_name, "Stevie Wonder")
        self.assertEqual(track.album_title, "Talking Book")
        self.assertEqual(track.album_title_display, "Talking Book")
        self.assertEqual(track.track_title, "You Are The Sunshine Of My Life")
        self.assertEqual(track.label, "Warner Bros.")
        self.assertEqual(track.label_display, "Warner Bros.")
        self.assertEqual(track.notes, 
                "This track is a bit played out but it still has some nice melodies")
                
        # for sanity, not real tests:
        self.assertEqual(
            track.established_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])
        self.assertEqual(
            track.modified_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])
    
    def test_partial_track_by_free_entry(self):
        selector = create_dj()
        playlist = ChirpBroadcast()
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="Stevie Wonder",
            freeform_track_title='You Are The Sunshine Of My Life'
        )
        track.put()
        self.assertEqual(track.album_title_display, "[Unknown Album]")
        self.assertEqual(track.label_display, "[Unknown Label]")
    
    def test_recent_tracks(self):
        playlist = ChirpBroadcast()
        selector = create_dj()
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="Autechre",
            freeform_album_title="Amber",
            freeform_track_title="Ember"
        )
        track.put()
        time.sleep(0.4)
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="The Meters",
            freeform_album_title="Chicken Strut",
            freeform_track_title="Hand Clapping Song"
        )
        track.put()
        
        recent_tracks = [t for t in playlist.recent_tracks]
        self.assertEqual(recent_tracks[0].track_title,
            "Hand Clapping Song")
        self.assertEqual(recent_tracks[1].track_title,
            "Ember")

class TestPlaylistBreak(PlaylistEventTest):
    
    def test_break(self):
        playlist = ChirpBroadcast()
        selector = create_dj()
        
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="The Meters",
            freeform_album_title="Chicken Strut",
            freeform_track_title="Hand Clapping Song"
        )
        track.put()
        time.sleep(0.4)
        
        pl_break = PlaylistBreak(playlist=playlist)
        pl_break.put()
        
        self.assertEqual(
            [type(e) for e in playlist.recent_tracks],
            [PlaylistTrack])
        
        self.assertEqual(
            [type(e) for e in playlist.recent_events],
            [PlaylistBreak, PlaylistTrack])
        
