<?

class ChirpApiException extends Exception { }
class NotFoundException extends ChirpApiException { }
class InvalidRequestException extends ChirpApiException { }
class DatabaseConnectionException extends ChirpApiException { }
class DatabaseQueryException extends ChirpApiException { }
class InvalidCredentialsException extends ChirpApiException { }

class ChirpApi {
  private $link;
  private $db_username;
  private $db_password;
  private $db_host;
  private $db_name;
  private $db_port;

  public function __construct($db_host, $db_username, $db_password, $db_name) {
    $this->db_username = $db_username;
    $this->db_port = 3306;
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
             $this->authenticate();
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
                 $request['time_played'],
                 $request['track_notes']
                 );
             }
             else {
               throw new InvalidRequestException($request['q'] . " requires a HTTP POST.");
             }
         }
         else if (strpos($request['q'], 'playlist/delete/') === 0) {
           $this->authenticate();
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

  // function to parse the http auth header
  private function http_digest_parse($txt) {
      // protect against missing data
      $needed_parts = array(
          'nonce'=>1, 
          'nc'=>1, 
          'cnonce'=>1, 
          'qop'=>1, 
          'username'=>1, 
          'uri'=>1, 
          'response'=>1);
      $data = array();
      $keys = implode('|', array_keys($needed_parts));

      preg_match_all('@(' . $keys . ')=(?:([\'"])([^\2]+?)\2|([^\s,]+))@', $txt, $matches, PREG_SET_ORDER);

      foreach ($matches as $m) {
        $data[$m[1]] = $m[3] ? $m[3] : $m[4];
        unset($needed_parts[$m[1]]);
      }

      return $needed_parts ? false : $data;
  }

  private function authenticate() {
      global $txpcfg;

      // Workaround for PHP in CGI mode.   $_SERVER['PHP_AUTH_DIGEST'] doesn't get set
      // so we have to set $_ENV['REDIRECT_HTTP_AUTHORIZATION'] with a RewriteRule
      if (isset($_ENV['REDIRECT_HTTP_AUTHORIZATION']) && !isset($_SERVER['PHP_AUTH_DIGEST'])) {
          $_SERVER['PHP_AUTH_DIGEST'] = $_ENV['REDIRECT_HTTP_AUTHORIZATION'];
      }

      if (empty($_SERVER['PHP_AUTH_DIGEST'])) {
          header('HTTP/1.1 401 Unauthorized');
          header('WWW-Authenticate: Digest realm="'.$txpcfg['api_auth_realm'].
                 '",qop="auth",nonce="'.uniqid().'",opaque="'.md5($txpcfg['api_auth_realm']).'"');
          throw new InvalidCredentialsException(); 
      }

      // analyze the PHP_AUTH_DIGEST variable
      $data = $this->http_digest_parse($_SERVER['PHP_AUTH_DIGEST']);
      if (!$data || !isset($txpcfg['api_auth_users'][$data['username']])) {
          throw new InvalidCredentialsException(); 
      }

      // generate the valid response
      $A1 = md5($data['username'] . ':' . $txpcfg['api_auth_realm'] . ':' . $txpcfg['api_auth_users'][$data['username']]);
      $A2 = md5($_SERVER['REQUEST_METHOD'].':'.$data['uri']);
      $valid_response = md5($A1.':'.$data['nonce'].':'.$data['nc'].':'.$data['cnonce'].':'.$data['qop'].':'.$A2);

      if ($data['response'] != $valid_response)
          throw new InvalidCredentialsException(); 
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
                          $dj_name, $time_played, $track_notes) {
    // Expiration time of "Article" should be one week after the date the song was played
    $expiration_time = strftime("%Y-%m-%d %H:%M:%S", strtotime("$posted_time +1 week"));
    $author_id = 'lovehasnologic'; // TODO: Make this configurable

    $this->db_connect();

    // Set the URL-only title so it's like "artist-song-title" so the full URL is like
    // http://chirpradio.org/playlists/1234/they-might-be-giants-your-racist-friend 
    //
    // Escape spaces with hyphens
    // E.g. jawbreaker-the-boat-dreams-from-the-hill
    //
    // The URL title needs to be be limited to 157 characters 
    // (200 minus 43 reserved for http://chirpradio.org/playlists/##########/)  
    $track_url_length = 157;
    $url_title = substr(sprintf("%s-%s",
                         str_replace(" ", "-", strtolower($track_artist)),
                         str_replace(" ", "-", strtolower($track_album))
                         ),
                         0, $track_url_length);

    // Insert information about the track into the Textpattern database as an article.
    // See http://code.google.com/p/chirpradio/issues/detail?id=44#c4 for more on
    // field mappings
    $query = sprintf("INSERT INTO textpattern (Posted, Expires, AuthorID, LastMod, Title, url_title, Body, Body_html, Excerpt, Excerpt_html, Annotate, AnnotateInvite, Status, textile_body, textile_excerpt, Section, Keywords, custom_1, custom_2, custom_3) " .
             "VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %d, '%s', %d, %d, %d, '%s', '%s', '%s', '%s', '%s')",
             $time_played,
             $expiration_time,
             $author_id,
             $time_played,
             $track_name,
             $url_title,
             $track_album,
             "<p>$track_album</p>",
             $track_notes,
             "<p>$track_notes</p>",
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
        $response = json_encode(
                      array('track_id' => $track_id,
                            'article_id' => $article_id,
                            'url_title' => $url_title)
                    ) . "\n";
      }
      else {
        throw new DatabaseQueryException('Database query failed: ' . mysql_error());
      }

    return $response;

  }

  private function current() {
    $this->db_connect();
    $query = "SELECT ID AS article_id, Title AS track_title, Body AS track_album, Keywords AS track_artist, custom_1 AS track_label, custom_2 AS dj_name, custom_3 AS track_id, LastMod AS time_played, Excerpt as track_notes FROM textpattern WHERE Section = 'playlists' ORDER By LastMod DESC, id DESC LIMIT 1";
    if ($result = mysql_query($query)) {
      $current_track = mysql_fetch_object($result);
      $response = json_encode($current_track) . "\n";
    }
    else {
      throw new DatabaseQueryException('Database query failed: ' . mysql_error());
    }

    return $response;
  }

  private function delete($track_id) {
    $select_query = sprintf("SELECT ID AS article_id, custom_3 AS track_id FROM textpattern WHERE custom_3 = '%s'", $track_id);
    $delete_query = sprintf("DELETE FROM textpattern WHERE custom_3 = '%s'", $track_id);

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

?>
