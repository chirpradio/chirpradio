// requires: chirp/chirp.js
//           jquery.autocomplete/jquery.autocomplete.js

$(document).ready(function() {
    
    var default_opt = {
        selectFirst: false,
        minChars: 3,
        delay: 400,
        maxItemsToShow: 15,
        matchContains: true // tells the cache to do substring matches 
                            // (necessary when searching "eno" and the 
                            // result is "Eno, Brian")
    };
    
    $("#id_artist").keydown(function() {
        $(this).addClass('freeform');
    });
    $("#id_album").keydown(function() {
       $(this).addClass('freeform');
    });
    $("#id_song").keydown(function() {
        $(this).addClass('freeform');
    });

    $("#id_artist").autocomplete("/djdb/artist/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                var song = $("#id_song").get(0);
                song.autocompleter.setExtraParams({artist_key: entity_key});
                song.autocompleter.flushCache();
                $("#id_artist_key").attr("value", entity_key);
                $("#id_artist").focus();
                $("#id_artist").removeClass('freeform');
            }
        }, default_opt));
    
    $("#id_album").autocomplete("/djdb/album/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                $("#id_album_key").attr("value", entity_key);
                $("#id_album").focus();
                $("#id_album").removeClass('freeform');
            }
        }, default_opt));
    
    $("#id_song").autocomplete("/djdb/track/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                $("#id_song_key").attr("value", entity_key);
                $("#id_song").focus();
                $("#id_song").removeClass('freeform');
            }
        }, default_opt));
    
    // be sure that freeform entry always clears out any 
    // previously auto-completed keys :
    
    $("#id_artist").change(function() {
        var song = $("#id_song").get(0);
        song.autocompleter.setExtraParams({artist_key: ""});
        song.autocompleter.flushCache();
        $("#id_artist_key").attr("value", "");
    });
    $("#id_album").change(function() {
        $("#id_album_key").attr("value", "");
    });
    $("#id_song").change(function() {
        $("#id_song_key").attr("value", "");
    });
    
    $('#lookup-on-musicbrainz').click(function(e) {
        var url = 'http://musicbrainz.org/search/textsearch.html';
        var qs = 'limit=25&adv=on&handlearguments=1';
        var artist = $('#id_artist').val();
        var album = $('#id_album').val();
        var song = $('#id_song').val();
        if ( !artist ) {
            e.preventDefault();
            return;
        }
        if (artist && album) {
            qs += '&type=release';
            qs += '&query=' + escape('"' + album + '" AND artist:' + artist);
        } else if (artist && song) {
            qs += '&type=track';
            qs += '&query=' + escape('"' + song + '" AND artist:' + artist);
        } else {
            qs += '&type=artist';
            qs += '&query=' + escape(artist);
        }
        // console.log(qs);
        
        this.href = url + '?' + qs;
    });
    
    $('#lookup-album-on-google').click(function(e) {
        var url = 'http://google.com/search';
        var artist = $('#id_artist').val();
        var album = $('#id_album').val();
        if ( !artist && !album ) {
            e.preventDefault();
            return;
        }
        this.href = url + '?q=' + escape(artist + " " + album);
    });
    
    $('#pronounce-artist').click(function(e) {
        var url = 'http://google.com/search';
        var artist = $('#id_artist').val();
        if ( !artist ) {
            e.preventDefault();
            return;
        }
        this.href = url + '?q=' + escape(artist + " pronounced");
    });
});