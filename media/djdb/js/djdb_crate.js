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
});