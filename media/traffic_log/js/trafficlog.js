// requires: chirp/chirp.js
//           

chirp.traffic_log = {};

$(document).ready(function() {
    
    var ns = chirp.traffic_log;
    
    ns.handle_finish_spot = function(anchor, tr) {
        var url = $(anchor).attr("href");
        $.ajax({
            url: url,
            success: function(data, textStatus) {
                tr.removeClass("new");
                tr.addClass("finished");
            },
            error: function (XMLHttpRequest, textStatus, errorThrown) {
                alert("Whoops, there was an error on the server. An email has been sent to the admins so sit tight or try again.");
            }
        });
    };
    
    $("#refresh-button").click(function() {
        window.location = "/traffic_log/?t=" + Math.random().toString();
    });
    
    // $(document).bind('beforeReveal.facebox', function() {
    //     $('#facebox table').width(700);
    // });
    
    $('#modal-container').jqm({
        ajax: '@href',
        overlay: 75,
        modal: true,
        trigger: '.show-text-for-reading',
        onLoad: function(hash) {
            var tr = $(hash.t).parent().parent(); // a->td->tr
            // temporarily bind this function to the 
            // anchor in the popover window. then unbind it 
            // after it fires.
            var onclick = function(e) {
                e.preventDefault();
                var anchor = this;
                ns.handle_finish_spot(anchor, tr);
                hash.w.jqmHide();
                $(this).unbind("click", onclick);
            };
            $(".finish-spot-after-reading").click(onclick);
        }
    });
    
    $(".finish-spot").click(function(e) {
        e.preventDefault();
        var anchor = this;
        var tr = $(anchor).parent().parent(); // a->td->tr
        ns.handle_finish_spot(anchor, tr);
    });
    $('.filter-button').click(function(){
        var interval = $(this).attr('id');
        var selector = '#id_hour_list option';
        if(interval == 'reset') {
            $(selector).attr('selected', false);
        } else if (interval == 'every-hour'){
            $(selector).attr('selected', true);
        } else if (parseInt(interval, 10)){
            $(selector).attr('selected', true);
            $.each($(selector), function(key,val){
                if($(val).val() % parseInt(interval, 10)) {
                    $(this).attr('selected', false);
                }
            });
        } else {
            selector = selector + interval;
            $(selector).attr('selected', true);
        }
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