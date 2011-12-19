(function($) {
"use strict";

var trackCache = {},
    currentTrackId,
    blankAlbumCover,
    chirpIconUrl,
    connectToFacebook,
    apiSource,
    $appRoot,
    _localOffset;

$(function() {
    $appRoot = $('.app-root');
    blankAlbumCover = $appRoot.attr('data-blank-album-cover');
    chirpIconUrl = $appRoot.attr('data-chirp-icon-url');
    connectToFacebook = $appRoot.attr('data-connect-to-facebook') == 'true';
    apiSource = $appRoot.attr('data-api-source');
    fetchTracks();
    window.setInterval(fetchTracks, 15000);
    $('.track-list').delegate('.post', 'click', function(evt) {
        evt.preventDefault();
        postTrackToWall($(this).attr('data-track-id'));
    });
    if (connectToFacebook) {
        // Load the SDK Asynchronously
        (function(d){
            var js, id = 'facebook-jssdk'; if (d.getElementById(id)) {return;}
            js = d.createElement('script'); js.id = id; js.async = true;
            js.src = "//connect.facebook.net/en_US/all.js";
            d.getElementsByTagName('head')[0].appendChild(js);
        }(document));
    }
});

window.fbAsyncInit = function() {
    $(function() {
        FB.init({
            appId: $appRoot.attr('data-app-id'),
            status: false, // check login status
            cookie: true, // enable cookies to allow the server to access the session
            xfbml: true, // parse XFBML
            channelURL: $appRoot.attr('data-channel-url')
        });
        // FB.Canvas.setAutoResize();
        FB.Canvas.setAutoGrow();
    });
};

function formatTime(hour, min) {
    var md = 'am';
    if (hour > 12) {
        hour = hour - 12;
        md = 'pm';
    } else if (hour == 12) {
        md = 'pm';
    }
    if (min < 10) {
        min = '0' + min.toString();
    }
    return hour.toString() + ':' + min.toString() + md;
}

function pushTrack($ctx, trk) {
    // It appears that instantiating a JavaScript Date object with a UTC
    // timestamp will put it in the local time zone.
    var localTime = new Date(parseInt(trk.played_at_gmt_ts, 10) * 1000);
    var fmtTime = formatTime(localTime.getHours(), localTime.getMinutes());
    var trkStr;
    trkStr = '<li id="track-' + trk.id + '">' +
        '<div class="time">' + fmtTime +
            '<img src="' + blankAlbumCover + '" height="32" width="32">' +
        '</div> ' +
        '<div class="track-info">' +
            '<span class="artist">' + trk.artist + '</span> ' +
            '<span class="track">' + trk.track + '</span> ' +
            '<span class="release">from ' + trk.release + '</span> ' +
            '<span class="label">(' + trk.label + ')</span>' +
        '</div>';
    if (connectToFacebook) {
        trkStr += ' <button class="post" data-track-id="' + trk.id + '">Share</button>';
    }
    trkStr += '<div class="cleared"></div></li>';
    $ctx.append(trkStr);
}

function postTrackToWall(trackId) {
    var trk = trackCache[trackId];
    if (typeof trk === 'undefined') {
        return;
    }
    var params = {
        method: 'feed',
        display: 'popup',
        link: 'http://apps.facebook.com/chirpradio/?ref=feed',  // direct link?
        picture: (trk.lastfm_urls.large_image || trk.lastfm_urls.med_image || chirpIconUrl),
        name: trk.artist + ': ' + trk.track + ' from ' + trk.release,
        caption: 'heard on CHIRPradio.org',
        description: trk.artist + ': ' + trk.track + ' from ' + trk.release + ' (' + trk.label + ')'
    };
    FB.ui(params, function(response) {
        // response['post_id']
    });
}

function fetchTracks() {
    $.ajax({url: '/api/current_playlist?src=' + apiSource,
            dataType: 'json',
            'type': 'GET',
            success: function(data) {
                updateTrackCache(data);  // in case we have new images for popups
                if (data.now_playing.id == currentTrackId) {
                    // nothing to update except artwork
                    updateAlbumArt(data);
                    return;
                }
                currentTrackId = data.now_playing.id;
                var $now = $('.ch-now-playing ul'),
                    $recent = $('.ch-recently-played ul');
                $('.ch-current-dj').text('(' + data.now_playing.dj + ')');
                $now.empty();
                pushTrack($now, data.now_playing);
                $recent.empty();
                $.each(data.recently_played, function(i, trk) {
                    pushTrack($recent, trk);
                });
                updateAlbumArt(data);
            },
            error: function(xhr, ajaxOptions, thrownError) {
                if (typeof console !== 'undefined') {
                    console.error(thrownError || 'unknown error');
                }
            }});

}

function updateAlbumArt(data) {
    var tracks = [data.now_playing];
    tracks = tracks.concat(data.recently_played);
    $.each(tracks, function(i, trk) {
        if (trk.lastfm_urls.sm_image) {
            $('#track-' + trk.id + ' img').attr('src', trk.lastfm_urls.sm_image);
        }
    });
}

function updateTrackCache(data) {
    trackCache[data.now_playing.id] = data.now_playing;
    $.each(data.recently_played, function(i, trk) {
        trackCache[trk.id] = trk;
    });
    // TODO(Kumar) clean up trackCache here
}

})($);


// From the live site player:

<!--
//v1.7
// Flash Player Version Detection
// Detect Client Browser type
// Copyright 2005-2008 Adobe Systems Incorporated.  All rights reserved.
var isIE  = (navigator.appVersion.indexOf("MSIE") != -1) ? true : false;
var isWin = (navigator.appVersion.toLowerCase().indexOf("win") != -1) ? true : false;
var isOpera = (navigator.userAgent.indexOf("Opera") != -1) ? true : false;
function ControlVersion()
{
    var version;
    var axo;
    var e;
    // NOTE : new ActiveXObject(strFoo) throws an exception if strFoo isn't in the registry
    try {
        // version will be set for 7.X or greater players
        axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.7");
        version = axo.GetVariable("$version");
    } catch (e) {
    }
    if (!version)
    {
        try {
            // version will be set for 6.X players only
            axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.6");

            // installed player is some revision of 6.0
            // GetVariable("$version") crashes for versions 6.0.22 through 6.0.29,
            // so we have to be careful.

            // default to the first public version
            version = "WIN 6,0,21,0";
            // throws if AllowScripAccess does not exist (introduced in 6.0r47)
            axo.AllowScriptAccess = "always";
            // safe to call for 6.0r47 or greater
            version = axo.GetVariable("$version");
        } catch (e) {
        }
    }
    if (!version)
    {
        try {
            // version will be set for 4.X or 5.X player
            axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.3");
            version = axo.GetVariable("$version");
        } catch (e) {
        }
    }
    if (!version)
    {
        try {
            // version will be set for 3.X player
            axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.3");
            version = "WIN 3,0,18,0";
        } catch (e) {
        }
    }
    if (!version)
    {
        try {
            // version will be set for 2.X player
            axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash");
            version = "WIN 2,0,0,11";
        } catch (e) {
            version = -1;
        }
    }

    return version;
}
// JavaScript helper required to detect Flash Player PlugIn version information
function GetSwfVer(){
    // NS/Opera version >= 3 check for Flash plugin in plugin array
    var flashVer = -1;

    if (navigator.plugins != null && navigator.plugins.length > 0) {
        if (navigator.plugins["Shockwave Flash 2.0"] || navigator.plugins["Shockwave Flash"]) {
            var swVer2 = navigator.plugins["Shockwave Flash 2.0"] ? " 2.0" : "";
            var flashDescription = navigator.plugins["Shockwave Flash" + swVer2].description;
            var descArray = flashDescription.split(" ");
            var tempArrayMajor = descArray[2].split(".");
            var versionMajor = tempArrayMajor[0];
            var versionMinor = tempArrayMajor[1];
            var versionRevision = descArray[3];
            if (versionRevision == "") {
                versionRevision = descArray[4];
            }
            if (versionRevision[0] == "d") {
                versionRevision = versionRevision.substring(1);
            } else if (versionRevision[0] == "r") {
                versionRevision = versionRevision.substring(1);
                if (versionRevision.indexOf("d") > 0) {
                    versionRevision = versionRevision.substring(0, versionRevision.indexOf("d"));
                }
            }
            var flashVer = versionMajor + "." + versionMinor + "." + versionRevision;
        }
    }
    // MSN/WebTV 2.6 supports Flash 4
    else if (navigator.userAgent.toLowerCase().indexOf("webtv/2.6") != -1) flashVer = 4;
    // WebTV 2.5 supports Flash 3
    else if (navigator.userAgent.toLowerCase().indexOf("webtv/2.5") != -1) flashVer = 3;
    // older WebTV supports Flash 2
    else if (navigator.userAgent.toLowerCase().indexOf("webtv") != -1) flashVer = 2;
    else if ( isIE && isWin && !isOpera ) {
        flashVer = ControlVersion();
    }
    return flashVer;
}
// When called with reqMajorVer, reqMinorVer, reqRevision returns true if that version or greater is available
function DetectFlashVer(reqMajorVer, reqMinorVer, reqRevision)
{
    versionStr = GetSwfVer();
    if (versionStr == -1 ) {
        return false;
    } else if (versionStr != 0) {
        if(isIE && isWin && !isOpera) {
            // Given "WIN 2,0,0,11"
            tempArray         = versionStr.split(" ");  // ["WIN", "2,0,0,11"]
            tempString        = tempArray[1];           // "2,0,0,11"
            versionArray      = tempString.split(",");  // ['2', '0', '0', '11']
        } else {
            versionArray      = versionStr.split(".");
        }
        var versionMajor      = versionArray[0];
        var versionMinor      = versionArray[1];
        var versionRevision   = versionArray[2];
            // is the major.revision >= requested major.revision AND the minor version >= requested minor
        if (versionMajor > parseFloat(reqMajorVer)) {
            return true;
        } else if (versionMajor == parseFloat(reqMajorVer)) {
            if (versionMinor > parseFloat(reqMinorVer))
                return true;
            else if (versionMinor == parseFloat(reqMinorVer)) {
                if (versionRevision >= parseFloat(reqRevision))
                    return true;
            }
        }
        return false;
    }
}
function AC_AddExtension(src, ext)
{
  if (src.indexOf('?') != -1)
    return src.replace(/\?/, ext+'?');
  else
    return src + ext;
}
function AC_Generateobj(objAttrs, params, embedAttrs)
{
  var str = '';
  if (isIE && isWin && !isOpera)
  {
    str += '<object ';
    for (var i in objAttrs)
    {
      str += i + '="' + objAttrs[i] + '" ';
    }
    str += '>';
    for (var i in params)
    {
      str += '<param name="' + i + '" value="' + params[i] + '" /> ';
    }
    str += '</object>';
  }
  else
  {
    str += '<embed ';
    for (var i in embedAttrs)
    {
      str += i + '="' + embedAttrs[i] + '" ';
    }
    str += '> </embed>';
  }
  document.write(str);
}
function AC_FL_RunContent(){
  var ret =
    AC_GetArgs
    (  arguments, ".swf", "movie", "clsid:d27cdb6e-ae6d-11cf-96b8-444553540000"
     , "application/x-shockwave-flash"
    );
  AC_Generateobj(ret.objAttrs, ret.params, ret.embedAttrs);
}
function AC_SW_RunContent(){
  var ret =
    AC_GetArgs
    (  arguments, ".dcr", "src", "clsid:166B1BCA-3F9C-11CF-8075-444553540000"
     , null
    );
  AC_Generateobj(ret.objAttrs, ret.params, ret.embedAttrs);
}
function AC_GetArgs(args, ext, srcParamName, classid, mimeType){
  var ret = new Object();
  ret.embedAttrs = new Object();
  ret.params = new Object();
  ret.objAttrs = new Object();
  for (var i=0; i < args.length; i=i+2){
    var currArg = args[i].toLowerCase();
    switch (currArg){
      case "classid":
        break;
      case "pluginspage":
        ret.embedAttrs[args[i]] = args[i+1];
        break;
      case "src":
      case "movie":
        args[i+1] = AC_AddExtension(args[i+1], ext);
        ret.embedAttrs["src"] = args[i+1];
        ret.params[srcParamName] = args[i+1];
        break;
      case "onafterupdate":
      case "onbeforeupdate":
      case "onblur":
      case "oncellchange":
      case "onclick":
      case "ondblclick":
      case "ondrag":
      case "ondragend":
      case "ondragenter":
      case "ondragleave":
      case "ondragover":
      case "ondrop":
      case "onfinish":
      case "onfocus":
      case "onhelp":
      case "onmousedown":
      case "onmouseup":
      case "onmouseover":
      case "onmousemove":
      case "onmouseout":
      case "onkeypress":
      case "onkeydown":
      case "onkeyup":
      case "onload":
      case "onlosecapture":
      case "onpropertychange":
      case "onreadystatechange":
      case "onrowsdelete":
      case "onrowenter":
      case "onrowexit":
      case "onrowsinserted":
      case "onstart":
      case "onscroll":
      case "onbeforeeditfocus":
      case "onactivate":
      case "onbeforedeactivate":
      case "ondeactivate":
      case "type":
      case "codebase":
      case "id":
        ret.objAttrs[args[i]] = args[i+1];
        break;
      case "width":
      case "height":
      case "align":
      case "vspace":
      case "hspace":
      case "class":
      case "title":
      case "accesskey":
      case "name":
      case "tabindex":
        ret.embedAttrs[args[i]] = ret.objAttrs[args[i]] = args[i+1];
        break;
      default:
        ret.embedAttrs[args[i]] = ret.params[args[i]] = args[i+1];
    }
  }
  ret.objAttrs["classid"] = classid;
  if (mimeType) ret.embedAttrs["type"] = mimeType;
  return ret;
}
// -->
