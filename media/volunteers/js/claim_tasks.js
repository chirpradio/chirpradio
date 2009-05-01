
// requires: chirp/chirp.js

$(document).ready(function() {
   
    $("div.claim_this_task a").click(function(event) {
        var that = $(this);
        var parent_div = that.parent();
        
        if (confirm(that.attr("ch_claim_prompt"))) {
            chirp.request({
                url: that.attr("href"),
                success: function(response) {
                    if (!response.success) {
                        // user error
                        alert("Error: " + response.error);
                        return;
                    }
                    $("a", parent_div).remove(); // not a link anymore
                    parent_div.attr("class", "claimed"); // change the style
                    // set name of volunteer who claimed the task:
                    parent_div.text(
                        response.user.first_name + " " + 
                        response.user.last_name);
                }
            });
        }
        event.preventDefault();
    });
});