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
from playlists.models import Playlist, PlaylistTrack
import auth.roles
from auth.models import User
from google.appengine.api.datastore_errors import BadValueError

__all__ = ['TestPlaylist', 'TestPlaylistTrack']

def create_dj():    
    dj = User(email="test")
    dj.roles.append(auth.roles.DJ)
    dj.put()
    return dj
    
def create_playlist():
    playlist = Playlist(playlist_type='live-stream')
    playlist.put()
    return playlist

class TestPlaylist(unittest.TestCase):
    
    def setUp(self):
        for obj in User.all():
            obj.delete()
    
    def test_non_dj_cannot_create_playlist(self):
        not_a_dj = User(email="test")
        not_a_dj.put()
        def make_playlist():
            playlist = Playlist(
                            created_by_dj=not_a_dj,
                            playlist_type="live-stream")
            playlist.put()
        self.assertRaises(ValueError, make_playlist)
    
    def test_unknown_playlist_type_raises_error(self):
        def make_playlist():
            playlist = Playlist(playlist_type="unknown-type")
            playlist.put()
        self.assertRaises(BadValueError, make_playlist)
    
    def test_playlist_creation(self):
        dj = create_dj()
        playlist = Playlist(created_by_dj=dj, playlist_type="live-stream")
        playlist.put()
        self.assertEqual(playlist.track_count, 0)
        self.assertEqual(
            playlist.established.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])
        self.assertEqual(
            playlist.modified.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])
            
        # for sanity, not real tests:
        self.assertEqual(
            playlist.established_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])
        self.assertEqual(
            playlist.modified_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])


class TestPlaylistTrack(unittest.TestCase):
    
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
    
    def test_track_missing_title_raises_error(self):
        selector = create_dj()
        def make_track():
            playlist = create_playlist()
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
            playlist = create_playlist()
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
        playlist = create_playlist()
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            artist=self.stevie,
            album=self.talking_book,
            track=self.tracks['You Are The Sunshine Of My Life']
        )
        track.put()
        self.assertEqual(track.artist_name, "Stevie Wonder")
        self.assertEqual(track.album.title, "Talking Book")
        self.assertEqual(track.track.title, "You Are The Sunshine Of My Life")
    
    def test_track_by_free_entry(self):
        selector = create_dj()
        playlist = create_playlist()
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
        self.assertEqual(track.track_title, "You Are The Sunshine Of My Life")
        self.assertEqual(track.label, "Warner Bros.")
        self.assertEqual(track.notes, 
                "This track is a bit played out but it still has some nice melodies")
                
        # for sanity, not real tests:
        self.assertEqual(
            track.established_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])
        self.assertEqual(
            track.modified_display.timetuple()[0:2],
            datetime.datetime.now().timetuple()[0:2])
        
    def test_track_number_is_set_automatically(self):
        selector = create_dj()
        playlist = create_playlist()
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="Stevie Wonder",
            freeform_album_title="Talking Book",
            freeform_track_title='You Are The Sunshine Of My Life'
        )
        track.put()
        self.assertEqual(track.track_number, 1)
        self.assertEqual(playlist.track_count, 1)
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="Squarepusher",
            freeform_track_title='Beep Street'
        )
        track.put()
        self.assertEqual(track.track_number, 2)
        self.assertEqual(playlist.track_count, 2)
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="Metallica",
            freeform_track_title='Master of Puppets'
        )
        track.put()
        self.assertEqual(track.track_number, 3)
        self.assertEqual(playlist.track_count, 3)
    
    def test_recent_tracks(self):
        playlist = create_playlist()
        selector = create_dj()
        track = PlaylistTrack(
            selector=selector,
            playlist=playlist,
            freeform_artist_name="Autechre",
            freeform_album_title="Amber",
            freeform_track_title="Ember"
        )
        track.put()
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
