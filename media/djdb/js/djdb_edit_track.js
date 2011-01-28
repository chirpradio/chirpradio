$(document).ready(function() {
    $("a[class^='edit_track']").unbind('click').click(function() {
        $("div[class^='edit_track']").slideUp("slow");
        $("div." + $(this).attr('class')).slideDown("slow");        
        return false;
    });
    $("input[class^='edit_track']").unbind('click').click(function() {
        $("div." + $(this).attr('class')).slideUp("slow");
        return false; 
    });

    var default_opt = {
    };
    $("input[name^='track_artist']").autocomplete("/djdb/artist/search.txt", 
        $.extend({
            onItemSelect: function(li, input) {
                var entity_key = li.extra[0];
                $("input[name='" + input.id + "']").attr("value", entity_key);
                $("input[name^='track_artist']").removeClass('freeform');
            }
        }, default_opt));
});

