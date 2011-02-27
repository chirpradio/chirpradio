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
    
    $("#id_artist").keyup(function() {
        if ($(this).val() === "")
            $(this).removeClass('freeform');
        else
            $(this).addClass('freeform');
    });
    $("#id_album").keyup(function() {
        if ($(this).val() === "")
            $(this).removeClass('freeform');
        else        
            $(this).addClass('freeform');
    });
    $("#id_song").keyup(function() {
        if ($(this).val() === "")
            $(this).removeClass('freeform');
        else
            $(this).addClass('freeform');
    });
    $("#id_label").keyup(function() {
        if ($(this).val() === "")
            $(this).removeClass('freeform');
        else
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
                var category = li.extra[1];
                if (category == 'heavy_rotation') {
                    $("#id_is_heavy_rotation").attr("checked", true);
                    $("#id_is_light_rotation").attr("checked", false);
                }
                else if (category == 'light_rotation') {
                    $("#id_is_light_rotation").attr("checked", true);
                    $("#id_is_heavy_rotation").attr("checked", false);
                }
                if (category == 'local_current') {
                    $("#id_is_local_current").attr("checked", true);
                    $("#id_is_local_classic").attr("checked", false);
                }
                else if (category == 'local_classic') {
                    $("#id_is_local_classic").attr("checked", true);
                    $("#id_is_local_current").attr("checked", false);
                }
            }
        }, default_opt));
    
    $("#id_song").autocomplete("/djdb/track/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                var entity_key = li.extra[0];
                $("#id_song_key").attr("value", entity_key);
                $("#id_song").focus();
                $("#id_song").removeClass('freeform');
                var category = li.extra[1];
                if (category == 'heavy_rotation') {
                    $("#id_is_heavy_rotation").attr("checked", true);
                    $("#id_is_light_rotation").attr("checked", false);
                }
                else if (category == 'light_rotation') {
                    $("#id_is_light_rotation").attr("checked", true);
                    $("#id_is_heavy_rotation").attr("checked", false);
                }
                if (category == 'local_current') {
                    $("#id_is_local_current").attr("checked", true);
                    $("#id_is_local_classic").attr("checked", false);
                }
                else if (category == 'local_classic') {
                    $("#id_is_local_classic").attr("checked", true);
                    $("#id_is_local_current").attr("checked", false);
                }
            }
        }, default_opt));
    
    $("#id_label").autocomplete("/djdb/label/search.txt", 
        $.extend({
            onItemSelect: function(li) {
                $("#id_label").focus();
                $("#id_label").removeClass('freeform');
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

    String.prototype.ltrim = function() {
	    return this.replace(/^\s+/,"");
    };

    function getCookie(cname) {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].ltrim();
            if (cookie.indexOf(cname) === 0) {
                return cookie.substring(cname.length + 1, cookie.length);
            }
        }
        return null;
    }
    
    function updateSentItem() {
        if ($("#id_allow_receive").attr("checked") === true) {
            item = getCookie("chirp_track_to_play");
            if (item !== null) {
                item = item.replace(/"/g, '');
                var fields = item.split(' / ');
                var artist_name = fields[0].trim().replace(/\/\//g, '/');
                var artist_key = fields[1].trim();
                var track_title = fields[2].trim().replace(/\/\//g, '/');
                var track_key = fields[3].trim();
                var album_title = fields[4].trim().replace(/\/\//g, '/');
                var album_key = fields[5].trim();
                var label = fields[6].trim().replace(/\/\//g, '/');
                var notes = fields[7].trim().replace(/\/\//g, '/');
                var categories = fields[8].trim().split(',');
                
                $("#id_artist").val(artist_name);
                $("#id_artist_key").val(artist_key);
                $("#id_song").val(track_title);
                $("#id_song_key").val(track_key);
                $("#id_album").val(album_title);
                $("#id_album_key").val(album_key);
                $("#id_label").val(label);
                $("#id_song_notes").val(notes);
                $("#id_is_heavy_rotation").attr("checked", false);
                $("#id_is_light_rotation").attr("checked", false);
                $("#id_is_local_current").attr("checked", false);
                $("#id_is_local_classic").attr("checked", false);            
                for (var i = 0; i < categories.length; i++) {
                    if (categories[i] == 'heavy_rotation') {
                        $("#id_is_heavy_rotation").attr("checked", true);
                        $("#id_is_light_rotation").attr("checked", false);
                    }
                    else if (categories[i] == 'light_rotation') {
                        $("#id_is_light_rotation").attr("checked", true);
                        $("#id_is_heavy_rotation").attr("checked", false);
                    }
                    if (categories[i] == 'local_current') {
                        $("#id_is_local_current").attr("checked", true);
                        $("#id_is_local_classic").attr("checked", false);
                    }
                    else if (categories[i] == 'local_classic') {
                        $("#id_is_local_classic").attr("checked", true);
                        $("#id_is_local_current").attr("checked", false);
                    }
                }
                document.cookie = 'chirp_track_to_play=; path=/; expires=Thu, 01-Jan-70 00:00:01 GMT;';
            }
            setTimeout(updateSentItem, 100);
        }
    }
    
    $("#id_allow_receive").click(function(e) {
        if ($(this).is(':checked')) {
            document.cookie = 'chirp_track_to_play=; path=/; expires=Thu, 01-Jan-70 00:00:01 GMT;';        
            updateSentItem();
        }
    });

    $('button[name=is_from_studio_override]').click(function(e) {
        // send POST to playlists app so middleware catches the studio ip override
        var button = $(this);
        e.preventDefault();
        $.post('/playlists/', {'is_from_studio_override': true}, function(data) {
          button.parent().parent().hide(300);
        });
    });
    
    updateSentItem();
});
