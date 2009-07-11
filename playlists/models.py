###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

"""Datastore model for DJ Playlists."""

from auth.models import User
from djdb.models import Artist, Album, Track
from google.appengine.ext import db
from google.appengine.api.datastore_types import Key
from common import time_util

class Playlist(db.Model):
    """A DJ playlist.
    """
    # DJ user who created the playlist, if relevant
    created_by_dj = db.ReferenceProperty(User, required=False)
    # The type of playlist.  Possible values: 
    #
    # live-stream
    #   The persistant CHIRP radio live stream.  There is only one 
    #   instance of this type of playlist.
    #
    # (more possible values TBD)
    playlist_type = db.CategoryProperty(required=True, choices=('live-stream',))
    # Number of tracks contained in this playlist.
    # This gets updated each time a PlaylistTrack() is saved
    track_count = db.IntegerProperty(default=0, required=True)
    # The date this playlist was established 
    # (automatically set to now upon creation)
    established = db.DateTimeProperty(auto_now_add=True)
    # The date this playlist was last modified (automatically set to now)
    modified = db.DateTimeProperty(auto_now=True)
    
    @property
    def established_display(self):
        return time_util.convert_utc_to_chicago(self.established)
        
    @property
    def modified_display(self):
        return time_util.convert_utc_to_chicago(self.modified)
    
    def validate(self):
        """Validate this instance before putting it to the datastore."""
        if self.created_by_dj:
            if not self.created_by_dj.is_dj:
                raise ValueError("User %r must be a DJ (user is: %r)" % (
                                    self.created_by_dj, self.created_by_dj.roles))
    
    def put(self, *args, **kwargs):
        self.validate()
        super(Playlist, self).put(*args, **kwargs)
    
    @property
    def recent_tracks(self):
        """Generates a list of recently played tracks in this playlist"""
        q = PlaylistTrack.all().filter('playlist =', self).order('-established')
        for track in q.fetch(1000):
            yield track

def LiveStream():
    """The chirp live stream"""
    
    # There is only one persistant live-stream stream.
    # If it doesn't exist, create it (probably only relevant for development)
    
    query = Playlist.all().filter('playlist_type =', 'live-stream')
    if query.count(1):
        playlist = query[0]
    else:
        playlist = Playlist(playlist_type='live-stream')
        playlist.put()
    
    return playlist

class PlaylistTrack(db.Model):
    """A track in a DJ playlist."""
    # The playlist this track belongs to
    playlist = db.ReferenceProperty(Playlist, required=True)
    # DJ user who selected this track.
    selector = db.ReferenceProperty(User, required=True)
    # Artist name if this is a freeform entry
    freeform_artist_name = db.StringProperty(required=False)
    # Reference to artist from CHIRP digital library (if exists in library)
    artist = db.ReferenceProperty(Artist, required=False)
    # Track title if this is a freeform entry
    freeform_track_title = db.StringProperty(required=False)
    # Reference to track (mp3 file) from CHIRP digital library (if exists in library)
    track = db.ReferenceProperty(Track, required=False)
    # The order at which this track appears in the playlist
    track_number = db.IntegerProperty(required=True, default=1)
    # Album title if this is a freeform entry
    freeform_album_title = db.StringProperty(required=False)
    # Reference to album from CHIRP digital library (if exists in library)
    album = db.ReferenceProperty(Album, required=False)
    # Label if this is a freeform entry
    freeform_label = db.StringProperty(required=False)
    # Notes about this track
    notes = db.TextProperty(required=False)
    # The date this playlist track was established 
    # (automatically set to now upon creation)
    established = db.DateTimeProperty(auto_now_add=True)
    # The date this playlist track was last modified (automatically set to now)
    modified = db.DateTimeProperty(auto_now=True)
    
    @property
    def artist_name(self):
        # validate() should enforce that one of these is available:
        if self.artist:
            return self.artist.name
        else:
            return self.freeform_artist_name
    
    @property
    def track_title(self):
        # validate() should enforce that one of these is available:
        if self.track:
            return self.track.title
        else:
            return self.freeform_track_title
    
    @property
    def album_title(self):
        if self.album:
            return self.album.title
        elif self.freeform_album_title:
            return self.freeform_album_title
        else:
            return None
    
    @property
    def established_display(self):
        return time_util.convert_utc_to_chicago(self.established)
        
    @property
    def modified_display(self):
        return time_util.convert_utc_to_chicago(self.modified)
    
    @property
    def label(self):
        # TODO(kumar) when a Label entity exists in the 
        # the DJDB then we should provide a way to fetch by reference
        if self.freeform_label:
            return self.freeform_label
        else:
            return None
    
    def __init__(self, *args, **kwargs):
        super(PlaylistTrack, self).__init__(*args, **kwargs)
        # TODO(kumar) wrap in a transaction?
        if isinstance(kwargs['playlist'], Key):
            playlist = Playlist.get(kwargs['playlist'])
        else:
            playlist = kwargs['playlist']
        track_number = playlist.track_count + 1
        playlist.track_count = track_number
        playlist.put()
        self.track_number = track_number
    
    def validate(self):
        """Validate this instance before putting it to the datastore.
        
        A track must have at least artist name and track title
        """
        if not self.track_title and not self.track:
            raise ValueError("Must set either a track_title or reference a track")
        if not self.artist_name and not self.artist:
            raise ValueError("Must set either an artist_name or reference an artist")
        if not self.selector.is_dj:
            raise ValueError("User %r must be a DJ (user is: %r)" % (
                                self.selector, self.selector.roles))
    
    def put(self, *args, **kwargs):
        self.validate()
        super(PlaylistTrack, self).put(*args, **kwargs)

