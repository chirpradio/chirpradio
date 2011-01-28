$(document).ready(function() {
    $("a.edit_artist").click(function() {
        $("div.edit_artist").slideDown("slow");
        return false;
    });
    $("input.edit_artist").click(function() {
        $("div.edit_artist").slideUp("slow");
        return false;
    });
});

