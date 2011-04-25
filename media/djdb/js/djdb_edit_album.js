$(document).ready(function() {
    $("a.edit_album").click(function() {
        $("div.edit_album").slideDown("slow");
        return false;
    });
    $("input.edit_album").click(function() {
        $("div.edit_album").slideUp("slow");
        return false;
    });
    $('#id_is_heavy_rotation').click(function(e) {
        if ($(this).is(':checked')) {
            $('#id_is_light_rotation').attr('checked', false);
        }
    });
    $('#id_is_light_rotation').click(function(e) {
        if ($(this).is(':checked')) {
            $('#id_is_heavy_rotation').attr('checked', false);
        }
    });
    $('#id_is_local_current').click(function(e) {
        if ($(this).is(':checked')) {
            $('#id_is_local_classic').attr('checked', false);
        }
    });
    $('#id_is_local_classic').click(function(e) {
        if ($(this).is(':checked')) {
            $('#id_is_local_current').attr('checked', false);
        }
    });
});

