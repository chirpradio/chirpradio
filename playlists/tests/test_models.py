
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

class TestPlaylist(unittest.TestCase):
    
    def setUp(self):
        for obj in User.all():
            obj.delete()
    
    def test_non_dj_cannot_create_playlist(self):
        not_a_dj = User(email="test")
        not_a_dj.put()
        def make_playlist():
            playlist = Playlist(
                            dj_user=not_a_dj,
                            playlist_type="on-air")
            playlist.put()
        self.assertRaises(ValueError, make_playlist)
    
    def test_unknown_playlist_type_raises_error(self):
        dj = create_dj()
        def make_playlist():
            playlist = Playlist(
                            dj_user=dj,
                            playlist_type="unknown-type")
            playlist.put()
        self.assertRaises(BadValueError, make_playlist)
    
    def test_playlist_creation(self):
        dj = create_dj()
        playlist = Playlist(dj_user=dj, playlist_type="on-air")
        playlist.put()
        self.assertEqual(playlist.track_count, 0)
        self.assertEqual(
            playlist.established.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])
        self.assertEqual(
            playlist.modified.timetuple()[0:4],
            datetime.datetime.now().timetuple()[0:4])


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
    
    def create_playlist(self):
        dj = create_dj()
        playlist = Playlist(dj_user=dj, playlist_type='on-air')
        playlist.put()
        return playlist
    
    def test_track_missing_title_raises_error(self):
        def make_track():
            playlist = self.create_playlist()
            track = PlaylistTrack(
                playlist=playlist,
                artist=self.stevie,
                album=self.talking_book
            )
            track.put()
        self.assertRaises(ValueError, make_track)
    
    def test_track_missing_artist_raises_error(self):
        def make_track():
            playlist = self.create_playlist()
            track = PlaylistTrack(
                playlist=playlist,
                album=self.talking_book,
                track=self.tracks['You Are The Sunshine Of My Life']
            )
            track.put()
        self.assertRaises(ValueError, make_track)
    
    def test_track_by_references(self):
        playlist = self.create_playlist()
        track = PlaylistTrack(
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
        playlist = self.create_playlist()
        track = PlaylistTrack(
            playlist=playlist,
            freeform_artist_name="Stevie Wonder",
            album_title="Talking Book",
            track_title='You Are The Sunshine Of My Life'
        )
        track.put()
        self.assertEqual(track.artist_name, "Stevie Wonder")
        self.assertEqual(track.album_title, "Talking Book")
        self.assertEqual(track.track_title, "You Are The Sunshine Of My Life")
        
    def test_track_number_is_set_automatically(self):
        playlist = self.create_playlist()
        track = PlaylistTrack(
            playlist=playlist,
            freeform_artist_name="Stevie Wonder",
            album_title="Talking Book",
            track_title='You Are The Sunshine Of My Life'
        )
        track.put()
        self.assertEqual(track.track_number, 1)
        self.assertEqual(playlist.track_count, 1)
        track = PlaylistTrack(
            playlist=playlist,
            freeform_artist_name="Squarepusher",
            track_title='Beep Street'
        )
        track.put()
        self.assertEqual(track.track_number, 2)
        self.assertEqual(playlist.track_count, 2)
        track = PlaylistTrack(
            playlist=playlist,
            freeform_artist_name="Metallica",
            track_title='Master of Puppets'
        )
        track.put()
        self.assertEqual(track.track_number, 3)
        self.assertEqual(playlist.track_count, 3)
