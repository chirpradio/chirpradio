###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

import sys
import logging
import urllib, urllib2
import wsgiref.handlers
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from google.appengine.ext import webapp
from google.appengine.api import taskqueue
from common import dbconfig, in_dev
from playlists.models import PlaylistEvent
from common.utilities import as_encoded_str
from common.autoretry import AutoRetry

log = logging.getLogger()

"""
Publish Track being played to remote PHP server

URLs for PHP test server

    # status of last track published
    curl --digest -u chirpapi:chirpapi -v -X GET http://geoff.terrorware.com/hacks/chirpapi/playlist/current

    # create/publish track
    curl --digest -u chirpapi:chirpapi -v -X POST http://geoff.terrorware.com/hacks/chirpapi/playlist/create
         -d "track_name=s&track_label=l&track_artist=a&track_album=r&dj_name=d&time_played=2009-12-20 14:37&track_id=agpjaGlycHJhZGlvchMLEg1QbGF5bGlzdEV2ZW50GB0M"

    # delete previously published track using track_id from create
    curl --digest -u chirpapi:chirpapi -v -X DELETE http://geoff.terrorware.com/hacks/chirpapi/playlist/delete/agpjaGlycHJhZGlvchMLEg1QbGF5bGlzdEV2ZW50GB0M"
"""

# TODO(selizondo): bootstrap dbconfig production datastore
CHIRPAPI_USERNAME = dbconfig.get('chirpapi.username', 'chirpapi')
CHIRPAPI_PASSWORD = dbconfig.get('chirpapi.password', 'chirpapi')

class PlaylistEventListener(object):
    """Listens to creations or deletions of playlist entries."""

    def create(self, track):
        """This instance of PlaylistEvent was created."""
        raise NotImplementedError

    def delete(self, track_key):
        """The key of this PlaylistEvent was deleted."""
        raise NotImplementedError

class LiveSiteListener(PlaylistEventListener):
    """Sends playlist events to the live CHIRP site (a Textpattern PHP site)."""

    def create(self, track):
        """This instance of PlaylistEvent was created."""
        url_track_create(track)

    def delete(self, track_key):
        """The key of this PlaylistEvent was deleted."""
        url_track_delete(track_key)

class Live365Listener(PlaylistEventListener):
    """Sends playlist events as metadata to the Live 365 player."""

    def create(self, track):
        """This instance of PlaylistEvent was created.

        POST parameters and their meaning

        **member_name**
        Live365 member name

        **password**
        Live365 password

        **sessionid**
        Unused.  This is an alternative to user password and looks like
        membername:sessionkey as returned by api_login.cgi

        **version**
        Version of API request.  Currently this must be 2

        **filename**
        I think we can leave this blank because Live365 docs say they
        will use it to guess song and artist info if none was sent.

        **seconds**
        Length of the track in seconds.  Live365 uses this to refresh its
        popup player window thing.  So really we should probably set this to 60 or 120
        because DJs might be submitting playlist entries out of sync with when
        they are actually playing the songs.

        **title**
        Song title

        **album**
        Album title
        """
        taskqueue.add(url=reverse('playlists.send_track_to_live365'), params={'id':str(track.key())})
    
    def delete(self, track_key):
        """The key of this PlaylistEvent was deleted.

        I don't think this can be implemented for Live365
        """
        pass

class PlaylistEventDispatcher(object):

    def __init__(self, listeners):
        self.listeners = listeners

    def create(self, *args, **kw):
        for listener in self.listeners:
            listener.create(*args, **kw)

    def delete(self, *args, **kw):
        for listener in self.listeners:
            listener.delete(*args, **kw)

playlist_event_listeners = PlaylistEventDispatcher([
    LiveSiteListener(),
    Live365Listener()
])

def _urls(type='create'):
    urls = {
        'create': dbconfig.get('chirpapi.url.create','http://192.168.58.128:8101/api/track/'),
        'delete': dbconfig.get('chirpapi.url.delete','http://192.168.58.128:8101/api/track/'),
        #'create': dbconfig.get('chirpapi.url.create','http://geoff.terrorware.com/hacks/chirpapi/playlist/create'),
        #'delete': dbconfig.get('chirpapi.url.delete','http://geoff.terrorware.com/hacks/chirpapi/playlist/delete')
    }
    return urls[type]


"""Helper funcs used by playlists.views
"""
def url_track_create(track):
    if in_dev():
        _url_track_create(track)
    else:
        taskqueue.add(url=reverse('playlists.send_track_to_live_site'), params={'id':str(track.key())})

def url_track_delete(key):
    if in_dev():
        _url_track_delete(key)
    else:
        taskqueue.add(url=reverse('playlists.delete_track_from_live_site'), params={'id':key})



""" bluk of the remoting code
"""
def _url_track_create(track):
    log.info("chirpradio.org create track %s" % track.key())
    qs = {
        'track_name': as_encoded_str(track.track_title),
        'track_artist': as_encoded_str(track.artist_name),
        'dj_name': as_encoded_str(track.selector.effective_dj_name),
        'time_played': track.modified.strftime("%Y-%m-%d %H:%M:%S"),
        'track_id': str(track.key()),
    }
    # optional:
    if track.album_title:
        qs['track_album'] = as_encoded_str(track.album_title)
    if track.label:
        qs['track_label'] = as_encoded_str(track.label)
    if track.notes:
        qs['track_notes'] = as_encoded_str(track.notes)

    data = urllib.urlencode(qs)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    #
    url = _urls('create')
    #_fetch_url(url, data, 'POST', headers)
    return _fetch_url(url, data, 'POST', headers, 'digest', url)

def _url_track_delete(id):
    log.info("chirpradio.org delete track %s" % id)
    if not id:
        return
    #
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    #
    url = _urls('delete')
    #_fetch_url(url + str(id), {}, 'DELETE', headers)
    return _fetch_url(url + "/" + str(id), {}, 'DELETE', headers, 'digest', url)


"""urllib2.Request only supports GET|POST, extend it to support any HTTP method type
"""

class AnyRequest(urllib2.Request):

    def get_method(self):
        if hasattr(self, 'http_method'):
            return getattr(self, 'http_method')
        else:
            return urllib2.Request.get_method(self)

def _fetch_url(url=None, data=None, method='GET', headers=None, auth_type=None, auth_url=None):
    if headers is None:
        headers = {}

    # init auth hander if using http authentication
    if auth_type and auth_type in ('basic','digest'):
        _auth_handler(CHIRPAPI_USERNAME, CHIRPAPI_PASSWORD, auth_type, auth_url)

    try:
        # request
        req = AnyRequest(url, data, headers)
        req.http_method = method

        # response
        res = urllib2.urlopen(req)
        d = {'code': res.code, 'content': res.read(), 'success':True}
        log.info("URL success output: %s" % d)
        return d
    except AssertionError:
        # short of listing every possible urllib2 exception,
        # this is the best I can think of to get the test suite to work
        # (i.e. mock assertions) -Kumar
        raise
    except Exception, e:
        # raise
        etype, val, tb = sys.exc_info()
        log.error(e)
        if hasattr(e, 'read'):
            content = e.read()
        else:
            content = None
        log.info("URL error output: %s" % content)
        return {'success': False,
                'exception_type': etype.__name__,
                'exception': val,
                'content': content}

def _auth_handler(username, password, auth_type=None, auth_url=None):
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, auth_url, username, password)

    if auth_type == 'digest':
        handler = urllib2.HTTPDigestAuthHandler(password_mgr)
    else:
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)

    opener = urllib2.build_opener(handler)
    urllib2.install_opener(opener)


"""Thin wrapper for taskqueue actions mapped in playlists/urls.py
"""

def task_response(result):
    if not result['success']:
        return HttpResponse("Task was unsuccessful", status=500)
    else:
        return HttpResponse("OK")

def send_track_to_live_site(request):
    track = AutoRetry(PlaylistEvent).get(request.POST['id'])
    if not track:
        log.warning("Requested to create a non-existant track of ID %r" % request.POST['id'])
        # this is not an error (malicious POST, etc), so make sure the task succeeds:
        return  task_response({'success':True})
    else:
        result = _url_track_create(track)
        return task_response(result)

def delete_track_from_live_site(request):
    result = _url_track_delete(request.POST['id'])
    return task_response(result)

def send_track_to_live365(request):
    """Background Task URL to send playlist to Live 365 service.
    
    This view expects POST parameters:
    
    **id**
    The Datastore key of the playlist entry
    
    When POSTing to Live 365 here are the parameters:
    
    **member_name**
    Live365 member name
    
    **password**
    Live365 password
    
    **sessionid**
    Unused.  This is an alternative to user password and looks like
    membername:sessionkey as returned by api_login.cgi
    
    **version**
    Version of API request.  Currently this must be 2
    
    **filename**
    I think we can leave this blank because Live365 docs say they 
    will use it to guess song and artist info if none was sent.
    
    **seconds**
    Length of the track in seconds.  Live365 uses this to refresh its 
    popup player window thing.  So really we should probably set this to 60 or 120 
    because DJs might be submitting playlist entries out of sync with when 
    they are actually playing the songs.
    
    **title**
    Song title
    
    **artist**
    Artist name
    
    **album**
    Album title
    """
    track = AutoRetry(PlaylistEvent).get(request.POST['id'])
    if not track:
        log.warning("Requested to create a non-existant track of ID %r" % request.POST['id'])
        # this is not an error (malicious POST, etc), so make sure the task succeeds:
        return task_response({'success':True})
        
    log.info("Live365 create track %s" % track.key())
    
    qs = {
        'member_name': dbconfig['live365.member_name'],
        'password': dbconfig['live365.password'],
        'version': 2,
        'seconds': 30,
        'title': as_encoded_str(track.track_title, encoding='latin-1', errors="ignore"),
        'artist': as_encoded_str(track.artist_name, encoding='latin-1', errors="ignore"),
        'album': as_encoded_str(track.album_title, encoding='latin-1', errors="ignore")
    }
    data = urllib.urlencode(qs)
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    # in prod: http://www.live365.com/cgi-bin/add_song.cgi
    service_url = dbconfig['live365.service_url']
    result = _fetch_url(url=service_url, method='POST', data=data, headers=headers)
    return task_response(result)

