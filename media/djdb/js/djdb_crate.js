$(document).ready(function() {
    $("#sortable").sortable({
        update : function() {
            var order = $("#sortable").sortable('serialize');
            $("#reorder").load("/djdb/crate/reorder?" + order);
        }
    });
    $("input.remove_all_crate_items").click(function() {
        $("div.remove_all_crate_items").slideDown("slow");        
        return false;
    });
    $("input.cancel").click(function() {
        $("div.remove_all_crate_items").slideUp("slow");        
        return false;
    });
    $("a.send_to_playlist").unbind('click').click(function() {
        var img = jQuery("img", this);
        $.ajax({
            url: $(this).attr("href"),
            type: 'GET',
            error: function(data) {
                $('div.error').append(data.responseText);

                var win = window.open('','Error Sending to Playlist','scrollbars=1,width=600,height=400');
                var html = data.responseText;
                win.document.open();
                win.document.write(html);
                win.document.close();

                img.attr("src", "/media/common/img/play-error.png");
                setTimeout(function() { img.attr("src", "/media/common/img/play.png"); }, 1000);
            },
            success: function(data) {
                document.cookie = "chirp_track_to_play=" + data + "; path=/";
                img.attr("src", "/media/common/img/play-success.png");
                setTimeout(function() { img.attr("src", "/media/common/img/play.png"); }, 1000);
            }
        });

        return false;
    });
});

