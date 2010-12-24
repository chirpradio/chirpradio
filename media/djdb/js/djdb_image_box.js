// Based on Lumen by Kelli Shaver.
$.fn.image_box = function(options) {
    $(this).unbind('click').click(function() {
        var opt = $.extend({width: 600,
                            height: 400}, options);
        var image_box  = '<div id="image_box_wrapper"></div>';
        image_box     += '<div id="image_box">';
        image_box     += '  <div class="close"><a href="#">close</a> or escape</div>';
        image_box     += '  <div class="image"><img src="' + $(this).attr('href') + '" width="' + opt.width + '" height="' + opt.height + '"/></div>';
        image_box     += '</div>';

        $('body').append(image_box);

        // Center image box.        
        $('#image_box').css("position", "absolute");
        var x = $(window).width() / 2 - $('#image_box').outerWidth() / 2;
        var y = $(window).height() / 2.0 - $('#image_box').outerHeight() / 2;
        $('#image_box').css('left', x + $(window).scrollLeft());
        $('#image_box').css('top', y + $(window).scrollTop());
        $('#image_box_wrapper').css('left', $(window).scrollLeft());
        $('#image_box_wrapper').css('top', $(window).scrollTop());
        $('body').css('overflow', 'hidden');

        $('#image_box_wrapper').click(function() {
            hide_image_box();
        });
    
      	$('#image_box .close').click(function() {
        	hide_image_box();

         	return false;
       	});
      
        document.onkeyup = function(e) { 	
      		if (e === null) { // ie
      			keycode = event.keyCode;
      		}
            else { // mozilla
      			keycode = e.which;
      		}
      		if (keycode == 27){
      			hide_image_box();
      		}
      	};
      	  	
        function hide_image_box() {
          $('body').css('overflow', 'auto');
          $('#image_box').remove();
          $('#image_box_wrapper').remove();
        }
        
      	return false;
    });
};

$(document).ready(function() {
    var options = {width: 600,
                   height: 400};
    $('a.album_cover').image_box(options);
});

