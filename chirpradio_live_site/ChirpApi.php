class ChirpApiException extends Exception { }
class NotFoundException extends ChirpApiException { }
class InvalidRequestException extends ChirpApiException { }
class DatabaseConnectionException extends ChirpApiException { }
class DatabaseQueryException extends ChirpApiException { }

class ChirpApi {
  private $link;
  private $db_username;
  private $db_password;
  private $db_host;
  private $db_name;
  private $db_port;

  public function __construct($db_host, $db_port, $db_username, $db_password, $db_name) {
    $this->db_username = $db_username;
    $this->db_port = $db_port;
    $this->db_host = $db_host;
    $this->db_password = $db_password;
    $this->db_name = $db_name;
  }

  public function handle_request($request) {
      $method = $_SERVER['REQUEST_METHOD'];
      $response = NULL;

      if (isset($request['q'])) {
         // We were provided with a path (e.g. playlist/update or playlist/delete)
         // See if it's valid
         if ($request['q'] == 'playlist/current') {
             if ($method == 'GET') {
               $response = $this->current();
             }
             else {
               throw new InvalidRequestException($request['q'] . " requires a HTTP GET.");
             }
         }
         else if ($request['q'] == 'playlist/create') { 
             if ($method == 'POST') {
               // Check that API call has all the needed parameters
               $parameters = array(
                 'track_name',
                 'track_album',
                 'track_artist',
                 'track_label',
                 'dj_name',
                 'time_played',
                 'track_id'
               );
               foreach ($parameters as $parameter) {
                 if (!isset($request[$parameter])) {
                   throw new InvalidRequestException("Missing parameter " . $parameter);
                 }
               }

               // Correct HTTP method? check.  Needed parameters? check. Do it.
               $response = $this->create(
                 $request['track_id'],
                 $request['track_name'], 
                 $request['track_album'],
                 $request['track_artist'],
                 $request['track_label'],
                 $request['dj_name'],
                 $request['time_played']
                 );
             }
             else {
               throw new InvalidRequestException($request['q'] . " requires a HTTP POST.");
             }
         }
         else if (strpos($request['q'], 'playlist/delete/') === 0) {
           $track_id = substr($request['q'], strrpos($request['q'], '/') + 1);

           if ($method == 'DELETE') {
               $response = $this->delete($track_id);
             }
           else {
             throw new InvalidRequestException($request['q'] . " requires a HTTP DELETE.");
           }
         }
         else {
             throw new NotFoundException();
         }
      }
      else {
        // Apache + mod_rewrite didn't set the q parameter.  
        // This would only happen when someone tried to access index.php directly
        throw new NotFoundException();
      }

      return $response;
  }

  private function db_connect() {
    $link = mysql_connect($this->db_host . ':' . $this->db_port,
                                $this->db_username, $this->db_password); 
    if ($link) {
      $this->link = $link;
      mysql_select_db($this->db_name);
    }
    else {
      throw new DatabaseConnectionException('Cannot connect to database: ' . mysql_error());
    }

  }

  private function create($track_id, $track_name, $track_album, $track_artist, $track_label, 
                          $dj_name, $time_played) {
    // Expiration time of "Article" should be one week after the date the song was played
    $expiration_time = strftime("%Y-%m-%d %H:%M:%S", strtotime("$posted_time +1 week"));
    $author_id = 'lovehasnologic'; // TODO: Make this configurable

    $this->db_connect();

    // Insert information about the track into the Textpattern database as an article.
    // See http://code.google.com/p/chirpradio/issues/detail?id=44#c4 for more on
    // field mappings
    $query = sprintf("INSERT INTO textpattern (Posted, Expires, AuthorID, LastMod, Title, Body, Body_html, Annotate, AnnotateInvite, Status, textile_body, textile_excerpt, Section, Keywords, custom_1, custom_2, custom_3) " .
             "VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', %d, '%s', %d, %d, %d, '%s', '%s', '%s', '%s', '%s')",
             $time_played,
             $expiration_time,
             $author_id,
             $time_played,
             $track_name,
             $track_album,
             "<p>$track_album</p>",
             1,
             "Comment",
             4,
             1,
             1,
             "playlists",
             $track_artist,
             $track_label,
             $dj_name,
             $track_id
             );
    if ($result = mysql_query($query)) {
      $article_id = mysql_insert_id();
      // set as "id-artist-name-song-title" limiting the entire thing to no
      // more than 200 characters (http://chirpradio.org/playlists/.... needs to be < 200) 
      // So, the path needs to be < 168 chars
      // Escape spaces with hyphens
      // E.g. 2-jawbreaker-the-boat-dreams-from-the-hill
      $track_url_length = 168;
      $url_title = substr(sprintf("%d-%s-%s",
                           $article_id,
                           str_replace(" ", "-", strtolower($track_artist)),
                           str_replace(" ", "-", strtolower($track_album))
                           ),
                           0, $track_url_length);

      $query = sprintf("UPDATE textpattern SET url_title = '%s' WHERE ID = %d",
                       $url_title,
                       $track_id);
      if ($result = mysql_query($query)) {
        $response = json_encode(
                      array('track_id' => $track_id,
                            'article_id' => $article_id,
                            'url' => $url)
                    ) . "\n";
      }
      else {
        throw new DatabaseQueryException('Database query failed: ' . mysql_error());
      }
    }
    else {
      throw new DatabaseQueryException('Database query failed: ' . mysql_error());
    }

    return $response;

  }

  private function current() {
    $this->db_connect();
    $query = "SELECT ID AS track_id, Title AS track_title, Body AS track_album, Keywords AS track_artist, custom_1 AS track_label, custom_2 AS dj_name, custom_3 AS playlist_track_id, LastMod FROM textpattern WHERE Section = 'playlists' ORDER By LastMod DESC, id DESC LIMIT 1";
    if ($result = mysql_query($query)) {
      $current_track = mysql_fetch_object($result);
      $response = json_encode($current_track) . "\n";
    }
    else {
      throw DatabaseQueryException('Database query failed: ' . mysql_error());
    }

    return $response;
  }

  private function delete($track_id) {
    $select_query = sprintf("SELECT ID AS article_id, custom_3 AS track_id FROM textpattern WHERE custom_3 = '%d'", $id);
    $delete_query = sprintf("DELETE FROM textpattern WHERE custom_3 = '%d'", $id);

    $this->db_connect();

    if ($result = mysql_query($select_query)) {
      $track_to_delete = mysql_fetch_object($result);

      if ($result = mysql_query($delete_query)) {
        $response = json_encode($track_to_delete) . "\n";
      }
    }
    else {
      throw new NotFoundException('Track with ID ' . $track_id . ' not found.'); 
    }

    return $response;
  }
}
