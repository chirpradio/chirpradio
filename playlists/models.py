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
import logging

from google.appengine.ext.db import polymodel
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.api.datastore_types import Key

from auth.models import User
import auth
from djdb.models import Artist, Album, Track
from common import time_util
from common.autoretry import AutoRetry


log = logging.getLogger()


class Playlist(polymodel.PolyModel):
    """A playlist of songs.
    """
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

    @property
    def recent_tracks(self):
        """Generates a list of recently played tracks in this playlist"""
        q = PlaylistTrack.all().filter('playlist =', self).order('-established')
        for track in q.fetch(1000):
            yield track

    @property
    def recent_events(self):
        """Generates a list of recent events in this playlist.

        This is like self.recent_tracks but also includes breaks.
        """
        q = PlaylistEvent.all().filter('playlist =', self).order('-established')
        for event in q.fetch(1000):
            yield event

class DJPlaylist(Playlist):
    """A playlist created by a DJ.

    This might be in preparation for a show or just for organizational purposes.
    """
    # A name to identify this playlist by
    name = db.StringProperty(required=True)
    # DJ user who created the playlist, if relevant
    created_by_dj = db.ReferenceProperty(User, required=True)
    # Number of tracks contained in this playlist.
    # TODO(kumar) this is not currently used.
    track_count = db.IntegerProperty(default=0, required=True)

    def validate(self):
        """Validate this instance before putting it to the datastore."""
        if not self.created_by_dj.is_dj:
            raise ValueError("User %r must be a DJ (user is: %r)" % (
                                self.created_by_dj, self.created_by_dj.roles))

    def put(self, *args, **kwargs):
        self.validate()
        super(DJPlaylist, self).put(*args, **kwargs)

class BroadcastPlaylist(Playlist):
    """A continuous playlist for a live broadcast."""
    # The name of the broadcast channel
    channel = db.StringProperty(required=True)

def ChirpBroadcast():
    """The continuous CHIRP broadcast"""

    # There is only one persistant live-stream stream.
    # If it doesn't exist, create it once for all time

    query = BroadcastPlaylist.all().filter('channel =', 'CHIRP')
    if AutoRetry(query).count(1):
        playlist = AutoRetry(query)[0]
    else:
        playlist = BroadcastPlaylist(channel='CHIRP')
        AutoRetry(playlist).put()

    return playlist

def chirp_playlist_key():
    """Datastore key for the continuous CHIRP broadcast"""
    key_str = memcache.get('chirp_playlist')
    if not key_str:
        playlist = ChirpBroadcast()
        key_str = str(playlist.key())
        memcache.set('chirp_playlist', key_str)
    return db.Key(key_str)

class PlaylistEvent(polymodel.PolyModel):
    """An event that occurs in a Playlist."""
    # The playlist this event belongs to
    playlist = db.ReferenceProperty(Playlist, required=True)
    # The date this playlist event was established
    # (automatically set to now upon creation)
    established = db.DateTimeProperty(auto_now_add=True)
    # The date this playlist event was last modified (automatically set to now)
    modified = db.DateTimeProperty(auto_now=True)

    @property
    def established_display(self):
        return time_util.convert_utc_to_chicago(self.established)

    @property
    def modified_display(self):
        return time_util.convert_utc_to_chicago(self.modified)

class PlaylistBreak(PlaylistEvent):
    """A break in a playlist.

    Typically this is what a DJ will use to indicate that it's time
    to talk over the air.  The DJ would glance at the playlist and read
    aloud the four or five songs that were played since the last break
    """
    # this doesn't have any special fields

class PlaylistTrack(PlaylistEvent):
    """A track in a Playlist."""
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
    # Categories
    categories = db.StringListProperty(required=True)
    # True if LastFM URLs were already processed by the background task
    lastfm_urls_processed = db.BooleanProperty(required=False, default=False)
    # LastFM URL to small album image
    lastfm_url_sm_image = db.StringProperty(required=False)
    # LastFM URL to medium album image
    lastfm_url_med_image = db.StringProperty(required=False)
    # LastFM URL to large album image
    lastfm_url_large_image = db.StringProperty(required=False)

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
    def album_title_display(self):
        txt = self.album_title
        if txt:
            return txt
        else:
            return u"[Unknown Album]"

    @property
    def label(self):
        # TODO(kumar) when a Label entity exists in the
        # the DJDB then we should provide a way to fetch by reference
        if self.freeform_label:
            return self.freeform_label
        else:
            return None

    @property
    def label_display(self):
        txt = self.label
        if txt:
            return txt
        else:
            return u"[Unknown Label]"

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
        try:
            memcache.delete('api.current_track')
        except:
            log.exception('IGNORED while saving playlist:')

    def save(self, *args, **kwargs):
        return self.put(*args, **kwargs)


class PlayCount(db.Model):
    """A log of how many times each artist/track was played."""
    play_count = db.IntegerProperty(default=0)
    artist_name = db.StringProperty()
    album_title = db.StringProperty()
    established = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
