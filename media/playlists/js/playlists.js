// requires: chirp/chirp.js
//           jquery.autocomplete/jquery.autocomplete.js

$(document).ready(function() {
    $("#id_artist").autocomplete("/djdb/artist/search.txt", {
        selectFirst: false,
        onItemSelect: function(li) {
            var entity_key = li.extra[0];
            console.log("selected " + $(li).text() + " key: " + entity_key);
        }
    });
});