$(document).ready(function() {
    $("#sortable").sortable({
        update : function() {
            var order = $("#sortable").sortable('serialize');
            $("#reorder").load("/djdb/crate/reorder?" + order);
        }
    });

    var artist = $("#id_artist"),
		album = $("#id_album"),
		track = $("#id_track"),
        label = $("#id_label"),
		allFields = $([]).add(artist).add(album).add(track).add(label),
		tips = $("#validateTips");

    function updateTips(t) {
        tips.text(t).effect("highlight",{},1500);
    }

    function checkEmpty(o, n) {
        alert(o.val());
        if (o.val() == "") {
            o.addClass('ui-state-error');
            updateTips(n);
            return false;
        } else {
            return true;
        }
    }

    $("#dialog").dialog({
        bgiframe: true,
        autoOpen: false,
        height: 425,
        modal: true,
        buttons: {
            'Add Crate Item': function() {
                var bValid = true;
                allFields.removeClass('ui-state-error');

                if (artist.val() == '' && album.val() == '' && track.val() == '' && label.val() == '') {
                    updateTips('Please fill in at least one field.');
                }
                else {
//                    $("#reorder").load("/djdb/crate/add_item?response_page=crate&item_key=");
                    $(this).dialog('close');
                }
            },
            Cancel: function() {
                $(this).dialog('close');
            }
        },
        close: function() {
            allFields.val('').removeClass('ui-state-error');
        }
    });
    $("#add-crate-item").click(function() {
        $("#dialog").dialog('open');
    })
    .hover(
        function(){ 
            $(this).addClass("ui-state-hover"); 
        },
        function(){ 
            $(this).removeClass("ui-state-hover"); 
        }
    ).mousedown(function(){
        $(this).addClass("ui-state-active"); 
    })
    .mouseup(function(){
            $(this).removeClass("ui-state-active");
    });
});