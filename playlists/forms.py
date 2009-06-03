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

"""Forms for DJ playlists."""

import auth
from django.utils.translation import ugettext_lazy as _
from django.template import loader
from django import forms
from playlists.models import Playlist, PlaylistSong

class PlaylistForm(forms.Form):
    """
    Manage a song in a DJ playlist
    """
    artist = forms.CharField(label=_("Artist"))
    song_title = forms.CharField(label=_("Song Title"))
    album = forms.CharField(label=_("Album"))
    label = forms.CharField(label=_("Label"))
    song_notes = forms.CharField(label=_("Song Notes"), widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super(PlaylistForm, self).__init__(*args, **kwargs)

    def save(self):
        
        playlist = Playlist()
        playlist.user = auth.get_current_user()
        playlist.save()
        
        playlist_song = PlaylistSong()
        playlist_song.playlist = playlist
        playlist_song.save()
        return playlist_song
        