
// requires: chirp/chirp.js

$(document).ready(function() {
    
    $("#id_set_status_for_all").change(function(e) {
        e.preventDefault();
        var new_status = this.value;
        if (new_status !== "0") {
            $("select.status").attr("value", new_status);
        }
    });
    
});