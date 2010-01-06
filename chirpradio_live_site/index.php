<?php

require_once '../textpattern/config.php';
require_once 'ChirpApi.php';

try {
  $api = new ChirpApi($txpcfg['host'], $txpcfg['user'], $txpcfg['pass'], $txpcfg['db']);
  $response = $api->handle_request($_REQUEST);
  header('Content-type: application/json');
  echo $response;
}
catch (NotFoundException $e) {
  header("HTTP/1.0 404 Not Found");
}
catch (InvalidRequestException $e) {
  header('HTTP/1.1 400 Bad Request');
  echo $e->getMessage() . "\n";
}
catch (DatabaseConnectionException $e) {
  header('HTTP/1.1 500 Internal Server Error');
  echo $e->getMessage() . "\n";
}
catch (DatabaseQueryException $e) {
  header('HTTP/1.1 500 Internal Server Error');
  echo $e->getMessage() . "\n";
}
catch (InvalidCredentialsException $e) {
  header('HTTP/1.1 401 Unauthorized');
  echo "Invalid credentials\n";
}
catch (ChirpApiException $e) {
  // Catchall
  header('HTTP/1.1 503 Service Unavailable');
  echo "Service unavailable.\n";
}

?>
