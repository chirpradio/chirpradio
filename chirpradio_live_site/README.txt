API Methods

TODO: Put this in the code itself so it can be extracted with doxygen

API Method: playlist/create

Create a playlist entry on the live site.  This creates an "Article" entry in the Textpattern database.

HTTP Method(s):
POST

Requires authentication:
true (eventually, but not yet implemented)

Parameters:

* track_id. Required. Track ID from the Playlist app.
* track_name. Required. Title of currently played track.
* track_artist. Required. Artist name of currently played track
* track_album. Required.  Album title of the currently played track.
* track_label. Required. Name of record label that released the currently played track.
* dj_name. Required. Name of the DJ who played the track.
* time_played. Required. Time the track was played in the format "YYYY-MM-DD HH:MM:SS"

Response:

JSON structure with the Track ID (should match the one posted), Textpattern Article ID, and
Textpattern URL: 

{"track_id":15, "article_id":"15", "url":"http://chirpradio.org/playlists/2-jawbreaker-the-boat-dreams-from-the-hill"}

Usage example:

curl -d "track_name=Test Song&track_label=Test Label&track_album=Test Album&dj_name=Test DJ&time_played=2009-12-20 14:37&playlist_track_id=666" http://geoff.terrorware.com/hacks/chirpapi/playlist/create

API Method: playlist/current

Get the currently playing song (more accurately, the last playlist track article that Textpattern knows about).

HTTP Method(s):
GET

Requires authentication:
false

Parameters:
none

Response:

JSON structure with track article information:

{"id":"15","track_title":"Test Song","track_album":"Test Album","track_artist":"Test Band","track_label":"Test Label","dj_name":"Test DJ","playlist_track_id":"666","LastMod":"2009-12-20 14:37:00"}

Usage example:

curl -v http://geoff.terrorware.com/hacks/chirpapi/playlist/current

API Method: playlist/current

Get the currently playing song (more accurately, the last playlist track article that Textpattern knows about).

HTTP Method(s):
GET

Requires authentication:
false

Parameters:
none

Response:

JSON structure with track article information:

{"id":"15","track_title":"Test Song","track_album":"Test Album","track_artist":"Test Band","track_label":"Test Label","dj_name":"Test DJ","playlist_track_id":"666","LastMod":"2009-12-20 14:37:00"}

Usage example:

curl -v http://geoff.terrorware.com/hacks/chirpapi/playlist/current


API Method: playlist/delete/<track_id>

Delete a playlist article based on its Playlist App ID.

HTTP Method(s):
DELETE

Requires authentication:
true (but not yet implemented)

Parameters:
* track_id: Required.  Passed in URL.  The track ID from the Playlist App.

Response:

JSON structure with the article_id (from Textpattern), track_id (from Playlist App) of deleted track: 

{"article_id":"14","track_id":"666"}

Usage example:

curl -v -X DELETE http://geoff.terrorware.com/hacks/chirpapi/playlist/delete/playlist-app/666
