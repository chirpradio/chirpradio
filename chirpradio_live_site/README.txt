Installation

Copy the files to a directory named "api" in the Textpattern root directory.

Update the Textpattern rewrite rules to accomodate the new api directory by editing the .htaccess  and adding the following line:

  RewriteRule ^api/(.*)$ /api/index.php?q=$1 [L,QSA]

So the entire rule looks like this:

  RewriteCond %{REQUEST_URI} !=/favicon.ico 
  RewriteRule ^api/(.*)$ /api/index.php?q=$1 [L,QSA]
  RewriteRule ^(.*) index.php

Add the following lines to the bottom of the file <textpattern_root>/textpattern/config.sql:

  // API Authentication
  $txpcfg['api_auth_realm'] = 'CHIRP API';
  $txpcfg['api_auth_users'] = array(
      'chirpapi' => 'chirpapi',
  );

API Authentication

Some API methods require authentication.  Currently this is implemented with HTTP Digest Authentication.  For more information on this authentication method see http://en.wikipedia.org/wiki/Digest_access_authentication

API Methods

API Method: playlist/create

Create a playlist entry on the live site.  This creates an "Article" entry in the Textpattern database.

HTTP Method(s):
POST

Requires authentication:
true

Parameters:

* track_id. Required. Track ID from the Playlist app.
* track_name. Required. Title of currently played track.
* track_artist. Required. Artist name of currently played track
* track_album. Required.  Album title of the currently played track.
* track_label. Required. Name of record label that released the currently played track.
* dj_name. Required. Name of the DJ who played the track.
* time_played. Required. Time the track was played in the format "YYYY-MM-DD HH:MM:SS"
* track_notes. Optional. Additional Notes (Such as "Playing at Schuba's on Saturday").

Response:

JSON structure with the Track ID (should match the one posted), Textpattern Article ID, and
Textpattern URL path: 

{"track_id":"agpjaGlycHJhZGlvcg8LEghQbGF5bGlzdBiIBQw","article_id":3,"url_title":"test-artist-test-album"}

Usage example:

curl --digest --user chirpapi -d "track_name=Test Song&track_label=Test Label&track_artist=Test Artist&track_album=Test Album&dj_name=Test DJ&time_played=`date --rfc-3339=seconds`&track_id=agpjaGlycHJhZGlvcg8LEghQbGF5bGlzdBiIBQw&track_notes=Playing%20at%20Schuba's%20this%20Saturday" http://localhost/api/playlist/create

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

{"article_id":"3","track_title":"Test Song","track_album":"Test Album","track_artist":"Test Artist","track_label":"Test Label","dj_name":"Test DJ","track_id":"agpjaGlycHJhZGlvcg8LEghQbGF5bGlzdBiIBQw","time_played":"2010-01-06 15:02:48","track_notes":"Playing at Schuba's this Saturday"}

Usage example:

curl -v http://localhost/api/playlist/current


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

{"article_id":"26","track_id":"agpjaGlycHJhZGlvcg8LEghQbGF5bGlzdBiIBQw"}

Usage example:

curl --digest --user chirpapi  -v -X DELETE http://localhost/api/playlist/delete/agpjaGlycHJhZGlvcg8LEghQbGF5bGlzdBiIBQw
