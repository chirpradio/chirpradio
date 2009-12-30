// requires: chirp/chirp.js
//           

$(document).ready(function() {
    $("#refresh-button").click(function() {
        window.location = "/traffic_log/?t=" + Math.random().toString();
    });
});


// Kumar: might use this timer to display a notice but not a redirect
// because a DJ might be reading a spot when the timeout occurs

/*var start_timer = function() {
    var time = new Date();
    var hour = time.getHours();
    var minutes = time.getMinutes();
    var seconds = time.getSeconds();
    if ( seconds == 0 && minutes == 0 ) {
        window.location.replace( unescape( window.location.pathname ) ); 
    } else {
		if( minutes < 10 ){
			minutes = '0' + minutes;
		} 
		if ( seconds < 10 ){
			seconds = '0' + seconds;
		}

        self.status = hour + ":" + minutes +":" + seconds;
        self.setTimeout("start_timer()", 60)
    }
}*/