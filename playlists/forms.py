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
from playlists.models import Playlist, PlaylistTrack

class PlaylistTrackForm(forms.Form):
    """
    Manage a track in a DJ playlist
    """
    artist = forms.CharField(label=_("Artist"), 
                required=True, 
                widget=forms.TextInput(attrs={'class':'text'}),
                error_messages={'required':'Please enter the artist name.'})
    song_title = forms.CharField(label=_("Song Title"), 
                required=True,
                widget=forms.TextInput(attrs={'class':'text'}),
                error_messages={'required':'Please enter the song title.'})
    album = forms.CharField(label=_("Album"), 
                required=False,
                widget=forms.TextInput(attrs={'class':'text'}))
    label = forms.CharField(label=_("Label"), 
                required=False,
                widget=forms.TextInput(attrs={'class':'text'}))
    song_notes = forms.CharField(label=_("Song Notes"), 
                required=False,
                widget=forms.Textarea(attrs={'class':'text'}))

    def __init__(self, data=None, current_user=None):
        self.current_user = current_user
        super(PlaylistTrackForm, self).__init__(data=data)

    def save(self):
        if not self.current_user:
            raise ValueError("Cannot save() without a current_user")
        
        playlist = Playlist(
            dj_user=self.current_user,
            playlist_type='on-air')
        playlist.save()
        
        playlist_track = PlaylistTrack(playlist=playlist)
        # TODO(kumar) lookup relations when doing autocompletion
        playlist_track.freeform_artist_name = self.cleaned_data['artist']
        playlist_track.freeform_track_title = self.cleaned_data['song_title']
        if self.cleaned_data['album']:
            playlist_track.freeform_album_title = self.cleaned_data['album']
        # if self.cleaned_data['label']:
        #     playlist_track.label_title = self.cleaned_data['label']
        playlist_track.save()
        
        return playlist_track
        