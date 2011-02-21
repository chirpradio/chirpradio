// requires: chirp/chirp.js

var onair = {};

onair.enteredTrackData = {};

$(document).ready(function() {
    if ($('#onair').length) {
        onair.init();
    }
});

onair.adjustSpotText = function(spot, dir) {
    var curSize = spot.css('font-size');
    // Hmm, will it always be in pixels?
    curSize = parseFloat(curSize.replace(/px/, ''));
    if (dir == 'bigger') {
        spot.css('font-size', (curSize + 5).toString() + 'px');
    } else if (dir == 'smaller') {
        spot.css('font-size', (curSize - 5).toString() + 'px');
    }
};

onair.emptyFreeformInput = function() {
    $('#new-track-freeform').addClass('freeform-default');
    $('#new-track-freeform').val('Format: Artist / Song / Album / Label');
    $('#new-track-freeform').one('focus', function(e) {
        $(this).val('');
        $(this).removeClass('freeform-default');
    });
}

onair._id = 0;
onair.genId = function(prefix) {
    if (typeof prefix === undefined) {
        prefix = 'onair-';
    }
    onair._id += 1;
    return prefix + onair._id.toString();
}

onair.goOnAir = function(e) {
    $('button.onair').removeClass('off');
    $('button.onair').addClass('on');
    $('button.offair').removeClass('on');
    $('button.offair').addClass('off');
    $('.col1').hide();
    $('#new-track').hide();
    $('#mode').removeClass('offair');
    $('#mode').addClass('onair');
    var qlist = $('#onair-queued-list'),
        tracks = $('#queued-tracks .track');
    qlist.empty();
    if (tracks.length) {
        var tr = tracks.eq(0);
            d = $($('#played-track-template').html());
        $('.time', d).remove();
        qlist.append(d);
        onair.setTrackData(d, onair.getTrackData(tr));
    }
    onair.scrollToTop();
};

onair.goOffAir = function(e) {
    $('button.onair').removeClass('on');
    $('button.onair').addClass('off');
    $('button.offair').removeClass('off');
    $('button.offair').addClass('on');
    $('#mode').addClass('offair');
    $('#mode').removeClass('onair');
    $('#mode').addClass('offair');
    $('.col1').show();
    $('#new-track').show();
    onair.scrollToTop();
};

onair.getTrackData = function(elem) {
    elem = $(elem);
    var d = {
        // @TODO(Kumar) track key from server
        page_id: elem.attr('id'),
        artist: elem.attr('data-artist'),
        song: elem.attr('data-song'),
        album: elem.attr('data-album'),
        label: elem.attr('data-label')
    };
    return d;
};

onair.hideShowSpot = function(e) {
    var target = $(this);
    e.preventDefault();
    target.blur();
    if (target.text() == 'Hide') {
        target.text('Show');
    } else {
        target.text('Hide');
    }
    target.parents('.spot').children('p').toggle();
};

onair.init = function() {

    $('button.onair').click(function(e) {
        e.preventDefault();
        $(e.currentTarget).blur();
        $('#mode').trigger('onair');
    });

    $('button.offair').click(function(e) {
        e.preventDefault();
        $(e.currentTarget).blur();
        $('#mode').trigger('offair');
    });

    $('#finish-break').click(function(e) {
        e.preventDefault();
        $(e.currentTarget).blur();
        $('#mode').trigger('offair');
    });

    $('#mode').bind('onair', onair.goOnAir);
    $('#mode').bind('offair', onair.goOffAir);

    $('.spot .hide-show').live('click', onair.hideShowSpot);
    $('.spot .make-smaller').live('click', onair.makeSpotSmaller);
    $('.spot .make-bigger').live('click', onair.makeSpotBigger);

    onair.initTrackInput();

    $('#play-new-track').bind('click', function(e) {
        e.preventDefault();
        $(this).blur();
        $('#new-track').trigger('play', [onair.enteredTrackData]);
    }, false);

    $('#queue-new-track').bind('click', function(e) {
        e.preventDefault();
        $(this).blur();
        $('#new-track').trigger('queue', [onair.enteredTrackData]);
    }, false);

    $('#queue .track button.play').live('click', onair.playQueuedTrack);

    $('#new-track').bind('play', onair.playTrack);
    $('#new-track').bind('queue', onair.queueTrack);
};

onair.initTrackInput = function() {
    var keyWatch;
    onair.emptyFreeformInput();
    $('#new-track-freeform').bind('blur', function(e) {
        if ($(this).val() == '') {
            onair.emptyFreeformInput();
        }
    });
    $('#new-track-freeform').bind('keyup', function(e) {
        var target = $(e.target);
        if (keyWatch) {
            clearTimeout(keyWatch);
        }
        keyWatch = setTimeout(function() {
            var containsSlash = false,
                value = target.val();
            if (!value) {
                value = '';
            }
            if (value.indexOf('//') != -1) {
                value = value.replace(/(\/\/)/g, '{slash}');
                containsSlash = true;
            }
            var parts = value.split('/'),
                data = {artist: null,
                        song: null,
                        album: null,
                        label: null};
            if (value) {
                var p;
                for (var i=0; i < parts.length; i++) {
                    p = $.trim(parts[i]);
                    if (containsSlash) {
                        // Sweet child of miiiiiiine
                        p = p.replace(/\{slash\}/, '/');
                    }
                    switch (i) {
                        case 0: data.artist = p; break;
                        case 1: data.song = p; break;
                        case 2: data.album = p; break;
                        case 3: data.label = p; break;
                    }
                }
            }
            onair.enteredTrackData = data;
            $('#new-track .track-value').trigger('freeform',
                                                 [onair.enteredTrackData]);
        }, 100);
    });

    $('#new-track .track-value').bind('freeform', function(e, data) {
        var target = $(this), key = $(this).attr('id');
        target.children('.value').text(data[key] || '');
    });
};

onair.makeSpotBigger = function(e) {
    var target = $(this),
        spot = target.parents('.spot').children('p');
    e.preventDefault();
    target.blur();
    onair.adjustSpotText(spot, 'bigger');
};

onair.makeSpotSmaller = function(e) {
    var target = $(this),
        spot = target.parents('.spot').children('p');
    e.preventDefault();
    target.blur();
    onair.adjustSpotText(spot, 'smaller');
};

onair.playQueuedTrack = function(e) {
    e.preventDefault();
    $(this).blur();
    $(this).parents('.track').remove();
    $('#new-track').trigger('play', [onair.enteredTrackData]);
};

onair.playTrack = function(e, data) {
    onair.emptyFreeformInput();
    data.page_id = onair.genId('track-');
    var d = $('#track-loading-template').html();
    d = $(d);
    d.attr('id', data.page_id);
    $('#recent-playlist').prepend(d);
    onair.post('/playlists/api/play', data, onair.playTrackSuccess);
};

onair.playTrackSuccess = function(data) {
    var d = $('#' + data.page_id);
    d.removeClass('track-loading');
    d.empty().html($('#played-track-template .track').html());
    onair.setTrackData(d, data);
};

onair.post = function(url, data, onSuccess) {
    // @TODO(Kumar)
    // retry loop to post data to server then send data response to callback

    // simulate:
    console.log('pseudo-POST ' + url + ' ' + data);
    setTimeout(function() {
        onSuccess(data);
    }, 500);

};

onair.queueTrack = function(e, data) {
    onair.emptyFreeformInput();
    data.page_id = onair.genId('queue-track-');
    var d = $('#track-loading-template').html();
    d = $(d);
    d.attr('id', data.page_id);
    $('#queued-tracks').prepend(d);
    onair.post('/playlists/api/queue', data, onair.queueTrackSuccess);
};

onair.queueTrackSuccess = function(data) {
    var d = $('#' + data.page_id);
    d.removeClass('track-loading');
    d.empty().html($('#queued-track-template .track').html());
    onair.setTrackData(d, data);
};

onair.setTrackData = function(d, data) {
    $('.artist', d).text(data.artist || '');
    $('.song', d).text(data.song || '');
    $('.album', d).text(data.album || '');
    $('.label', d).text(data.label || '');
    // @TODO(Kumar) set data-key, etc
    d.attr('data-artist', data.artist || '');
    d.attr('data-song', data.song || '');
    d.attr('data-album', data.album || '');
    d.attr('data-label', data.label || '');
};

onair.scrollToTop = function() {
    $('html,body').animate({scrollTop: 0}, 50);
}
