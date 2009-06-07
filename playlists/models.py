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

from auth.models import User
from google.appengine.ext import db

class Playlist(db.Model):
    """A DJ playlist.
    """
    # DJ user
    user = db.ReferenceProperty(User, required=True)
    

class PlaylistSong(db.Model):
    """A song in a DJ playlist."""
    db.ReferenceProperty(Playlist, required=True)