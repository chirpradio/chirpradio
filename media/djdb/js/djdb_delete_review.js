$(document).ready(function() {
    $("a[class^='delete_review']").click(function() {
        $("div." + $(this).attr('class')).slideDown("slow");        
        return false;
    });
    $("input[class^='delete_review']").click(function() {
        $("div." + $(this).attr('class')).slideUp("slow");
        return false; 
    });
    $("a[class^='delete_comment']").click(function() {
        $("div." + $(this).attr('class')).slideDown("slow");        
        return false;
    });
    $("input[class^='delete_comment']").click(function() {
        $("div." + $(this).attr('class')).slideUp("slow");
        return false; 
    });
});
