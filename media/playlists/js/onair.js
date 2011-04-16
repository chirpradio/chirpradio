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

onair.changeTrackData = function(data) {
    var newVal = '',
        props = ['artist', 'song', 'album', 'label'],
        count = 0;
    $.each(props, function(i, prop) {
        if (data[prop]) {
            newVal += data[prop] + ' / ';
            count += 1;
        }
    });
    var finished = count == props.length;
    $('#new-track-freeform').val(newVal);
    onair.enteredTrackData = data;
    if (!finished) {
        $('#new-track-freeform').focus();
    }
};

onair.emptyFreeformInput = function() {
    // $('#new-track-freeform').addClass('freeform-default');
    // $('#new-track-freeform').val('Format: Artist / Song / Album / Label');
    // $('#new-track-freeform').one('focus', function(e) {
    //     $(this).val('');
    //     $(this).removeClass('freeform-default');
    // });
};

onair._id = 0;
onair.genId = function(prefix) {
    if (typeof prefix === undefined) {
        prefix = 'onair-';
    }
    onair._id += 1;
    return prefix + onair._id.toString();
};

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

    onair.initAutocomplete();
};

onair.initTrackInput = function() {
    var keyWatch;
    onair.emptyFreeformInput();
    $('#new-track-freeform').bind('blur', function(e) {
        if ($(this).val() === '') {
            onair.emptyFreeformInput();
        }
    });
    $('#new-track-freeform').bind('keydown', function(e) {
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
                        default: break;
                    }
                }
            }
            if (data.artist == onair.enteredTrackData.artist) {
                data.artist_key = onair.enteredTrackData.artist_key;
            }
            onair.enteredTrackData = data;
            $('#new-track').trigger('freeform', [e.which,
                                                 onair.enteredTrackData]);
        }, 100);
    });

    // $('#new-track').bind('freeform', function(e, keyCode, data) {
    //     // Set up mirroring in form fields (if rendered on the page)
    //     $('#new-track .track-value').each(function(i, e) {
    //         var target = $(e),
    //             key = $(e).attr('id');
    //         target.children('.value').text(data[key] || '');
    //     })
    // });

    $('#new-track-freeform').focus();
};

onair.keys = {
    LEFT: 37,
    RIGHT: 39,
    UP: 38,
    DOWN: 40,
    DELETE: 8,
    TAB: 9,
    COMMAND: 224,
    CONTROL: 17,
    OPTION: 18
};

onair.initAutocomplete = function() {
    var autocomplete,
        querying = false,
        timeout,
        queued,
        completer = $('#new-track').onairAutocomp();

    $('#new-track').bind('freeform', function(e, keyCode, data) {
        switch (keyCode) {
            case onair.keys.LEFT:
            case onair.keys.RIGHT:
            case onair.keys.OPTION:
            case onair.keys.CONTROL:
            case onair.keys.COMMAND:
                return;
                break;
            case onair.keys.UP:
                completer.moveUp();
                return;
                break;
            case onair.keys.DOWN:
                completer.moveDown();
                return;
                break;
            case onair.keys.TAB:
                completer.selectCurrent();
                // e.stopPropagation();
                // e.preventDefault();
                return;
                break;
            default:
                break;
        }
        if (querying) {
            queued = data;
        } else {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                querying = false;
            }, 2000);
            querying = true;
            autocomplete = setTimeout(function() {
                var onComplete = function() {
                    querying = false;
                    if (queued) {
                        completer.query(queued, onComplete);
                        queued = null;
                    }
                };
                completer.query(data, onComplete);
            }, 600);
        }
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
    //console.log('pseudo-POST ' + url + ' ' + data);
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
};

$.fn.onairAutocomp = function() {
    if (typeof this._onairAC === 'undefined') {
        this._onairAC = new onair.Autocomp(this);
    }
    return this._onairAC;
};

onair.Autocomp = function(el) {
    this.$el = $(el);
    this.$ul = $('#freeform-autocomplete ul', this.$el);
    this.url = this.$el.attr('data-autocomplete-url');
    this.reset();
};

onair.Autocomp.prototype.hide = function() {
    $('#freeform-autocomplete', this.$el).hide();
};

onair.Autocomp.prototype.loadMatches = function(matches) {
    var that = this;
    that.reset();
    that.show();
    that.numMatches = matches.length;
    $.each(matches, function(id, m) {
        var txt = m.artist;
        that.data[id] = m;
        if (m.song) {
            txt += ' / ' + m.song + ' / ' + m.album;
        }
        if (m.label) {
            txt += ' / ' + m.label;
        }
        that.$ul.append('<li id="' + id + '">' + txt + '</li>');
    });
};

onair.Autocomp.prototype.move = function(dir) {
    var that = this,
        next = that.selected + dir;
    if (that.selected > -1) {
        $('li:eq(' + that.selected + ')', that.$el).removeClass('selected');
    }
    if (next >= that.numMatches) {
        next = that.numMatches-1;
    }
    else if (next < 0) {
        next = 0;
    }
    $('li:eq(' + next + ')', that.$el).addClass('selected');
    that.selected = next;
};

onair.Autocomp.prototype.moveDown = function() {
    return this.move(1);
};

onair.Autocomp.prototype.moveUp = function() {
    return this.move(-1);
};

onair.Autocomp.prototype.query = function(typedData, onComplete) {
    var that = this;
    return $.ajax({
        url: that.url,
        type: 'GET',
        data: {'artist': typedData.artist || '',
               'artist_key': typedData.artist_key || '',
               'song': typedData.song || ''},
        cache: true,
        dataType: 'json',
        success: function(data, textStatus, jqXHR) {
            that.loadMatches(data.matches);
            onComplete();
        }
    });
};

onair.Autocomp.prototype.reset = function() {
    var that = this;
    that.$ul.empty();
    that.selected = -1;
    that.numMatches = 0;
    that.data = [];
};

onair.Autocomp.prototype.selectCurrent = function() {
    var that = this,
        current = that.selected;
    if (that.selected < 0) {
        current = 0;
    }
    onair.changeTrackData(that.data[current]);
    that.hide();
};

onair.Autocomp.prototype.show = function() {
    $('#freeform-autocomplete', this.$el).show();
};
