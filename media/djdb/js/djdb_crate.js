$(document).ready(function() {
    $("#sortable").sortable({
        update : function() {
            var order = $("#sortable").sortable('serialize');
            $("#reorder").load("/djdb/crate/" + crate_key + "/reorder?" + order);
        }
    });
    $("input.remove_all_crate_items").click(function() {
        $("div.remove_crate").slideUp("slow");
        $("div.remove_all_crate_items").slideDown("slow");        
        return false;
    });
    $("input.remove_crate").click(function() {
        $("div.remove_all_crate_items").slideUp("slow");
        $("div.remove_crate").slideDown("slow");        
        return false;
    });
    $("input.cancel").click(function() {
        $("div.remove_all_crate_items").slideUp("slow");
        $("div.remove_crate").slideUp("slow");
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
    $('#id_crates').change(function(e) {
        window.location = "/djdb/crate/" + $(this).attr('value');
    });

    $('a.select_all').click(function() {
        $("input.[name^='crate_item']").each(function() {
            this.checked = true;
        });
        return false;
    });		
    $('a.select_none').click(function() {
        $("input.[name^='crate_item']").each(function() {
            this.checked = false;
        });
        return false;
    });		
});

