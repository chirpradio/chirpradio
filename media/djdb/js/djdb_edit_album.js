$(document).ready(function() {
    $("a.edit_album").click(function() {
        $("div.edit_album").slideDown("slow");
        return false;
    });
    $("input.edit_album").click(function() {
        $("div.edit_album").slideUp("slow");
        return false;
    });
});

