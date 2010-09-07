$(document).ready(function() {
    $('a.open_search_help').click(function() {
        $("div.search_help").slideDown("slow");
        return false;
    });
    $('a.close_search_help').click(function() {
        $("div.search_help").slideUp("slow");
        return false;
    });    
});
