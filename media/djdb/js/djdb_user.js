$(document).ready(function() {
    var default_opt = {
    };
    
    $("#id_user").autocomplete("/auth/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                $("#id_user_key").attr("value", entity_key);
                $("#id_user").focus();
            }
        }, default_opt)
    );
    
    // be sure that freeform entry always clears out any 
    // previously auto-completed keys :
    $("#id_user").change(function() {
        $("#id_user_key").attr("value", "");
    });
    
    $("#id_author").autocomplete("/auth/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                $("#id_author_key").attr("value", entity_key);
                $("#id_author").focus();
            }
        }, default_opt)
    );
    
    // be sure that freeform entry always clears out any 
    // previously auto-completed keys :
    $("#id_author").change(function() {
        $("#id_author_key").attr("value", "");
    });
});