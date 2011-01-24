$(document).ready(function() {
    $("a[class^='edit_track']").click(function() {
        $("div." + $(this).attr('class')).slideDown("slow");        
        return false;
    });
    $("input[class^='edit_track']").click(function() {
        $("div." + $(this).attr('class')).slideUp("slow");
        return false; 
    });
    var default_opt = {
    };

    $("input[name^='track_artist']").keydown(function() {
        $(this).addClass('freeform');
    });

    $("input[name^='track_artist']").autocomplete("/djdb/artist/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                $("#id_artist_key").attr("value", entity_key);
                $("input[name=^='track_artist']").removeClass('freeform');
            }
        }, default_opt));

    $("input[name^='track_artist']").change(function() {
        $("#id_artist_key").attr("value", "");
    });
});

