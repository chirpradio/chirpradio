// requires: chirp/chirp.js
//           

$(document).ready(function() {
    $("#refresh-button").click(function() {
        window.location = "/traffic_log/?t=" + Math.random().toString();
    });
    
    // $(document).bind('beforeReveal.facebox', function() {
    //     $('#facebox table').width(700);
    // });
    
    $(".show-text-for-reading").click(function() {
        var id = $(this).attr("id");
        var parts = id.split("spot-read__");
        if (parts.length != 2) {
            throw new Error("Unexpected id for input: " + id);
        }
        var key = parts[1];
        $.facebox(function() {
            $.ajax({
                url: '/traffic_log/spot/text-for-reading/' + key,
                success: function(data, textStatus) {
                    $.facebox(data);
                },
                error: function (XMLHttpRequest, textStatus, errorThrown) {
                    alert("Whoops, there was an error on the server. An email has been sent to the admins so sit tight or try again.");
                    $(document).trigger('close.facebox');
                }
            });
        });
    });
    
    // sigh. this is all necessary to override the image paths:
    $.extend($.facebox.settings, {
        loadingImage : '/media/common/js/jquery-facebox/loading.gif',
        closeImage   : '/media/common/js/jquery-facebox/closelabel.gif',
        faceboxHtml  : '\
    <div id="facebox" style="display:none;"> \
      <div class="popup"> \
        <table> \
          <tbody> \
            <tr> \
              <td class="tl"/><td class="b tb"/><td class="tr"/> \
            </tr> \
            <tr> \
              <td class="b"/> \
              <td class="body"> \
                <div class="content"> \
                </div> \
                <div class="footer"> \
                  <a href="#" class="close"> \
                    <img src="/media/common/js/jquery-facebox/closelabel.gif" title="close" class="close_image" /> \
                  </a> \
                </div> \
              </td> \
              <td class="b"/> \
            </tr> \
            <tr> \
              <td class="bl"/><td class="b"/><td class="br"/> \
            </tr> \
          </tbody> \
        </table> \
      </div> \
    </div>'
        }
    );
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