$(document).ready(function() {
    $("#sortable").sortable({
        update : function() {
            var order = $("#sortable").sortable('serialize');
            $("#reorder").load("/djdb/crate/reorder?" + order);
        }
    });
});