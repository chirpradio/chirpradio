// requires: chirp/chirp.js
//           jquery.autocomplete/jquery.autocomplete.js

$(document).ready(function() {
    
    $("#id_artist").autocomplete("/djdb/artist/search.txt", {
        selectFirst: false,
        onItemSelect: function(li) {
            var entity_key = li.extra[0];
            $("#id_artist_key").attr("value", entity_key);
        }
    });
    
    $("#id_album").autocomplete("/djdb/album/search.txt", {
        selectFirst: false,
        onItemSelect: function(li) {
            var entity_key = li.extra[0];
            $("#id_album_key").attr("value", entity_key);
        }
    });
    
});