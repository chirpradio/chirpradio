// Based on Lumen by Kelli Shaver.
jQuery.fn.image_box = function(options) {
    jQuery(this).unbind('click').click(function() {
        var settings = jQuery.extend({width: 600,
                                      height: 400}, options);
        var image_box  = '<div id="image_box_wrapper"></div>';
        image_box     += '<div id="image_box">';
        image_box     += '  <div class="close"><a href="#">close</a> or escape</div>';
        image_box     += '  <div class="image"><img src="' + jQuery(this).attr('href') + '" width="' + settings.width + '" height="' + settings.height + '"/></div>';
        image_box     += '</div>';

        jQuery('body').append(image_box);
        var yOffset = jQuery(window).scrollTop();
        var xOffset = jQuery('#image_box').offset();
        jQuery('#image_box').css('width', settings.width + 'px');
        jQuery('#image_box .title').css('width', settings.width + 'px');
        jQuery('#image_box').css('height', settings.height + 20 + 'px');
        jQuery('#image_box').css('margin-top', yOffset + parseInt((jQuery(document).height() - 50 - jQuery('#image_box').height()) / 2) + 'px');
        jQuery('#image_box').css('margin-left', xOffset.left + parseInt((jQuery(document).width() - jQuery('#image_box').width()) / 2) + 'px');
        jQuery('#image_box_wrapper').css('height', jQuery(document).height() + 50 + 'px');
        jQuery('#image_box_wrapper').css('width', jQuery(window).width() + 50 + 'px');
        jQuery('body').css('overflow', 'hidden');
        jQuery('#image_box_wrapper').click(function() {
            hide_image_box();
        });
    
      	jQuery('#image_box .close').click(function() {
        	hide_image_box();

         	return false;
       	});
      
        document.onkeyup = function(e) { 	
      		if (e == null) { // ie
      			keycode = event.keyCode;
      		}
            else { // mozilla
      			keycode = e.which;
      		}
      		if (keycode == 27){
      			hide_image_box();
      		}	
      	}
      	  	
        function hide_image_box() {
          jQuery('body').css('overflow', 'auto');
          jQuery('#image_box').remove();
          jQuery('#image_box_wrapper').remove();
        }
        
      	return false;
    });
};

$(document).ready(function() {
    var options = {width: 600,
                   height: 400};
    $('a.album_cover').image_box(options);
});

