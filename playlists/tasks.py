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

import logging
import urllib, urllib2
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api.labs import taskqueue
from common import dbconfig, in_dev
from playlists.models import PlaylistEvent

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


def _urls(type='create'):
    urls = {
        #'create': dbconfig.get('chirpapi.url.create','http://192.168.58.128:8101/api/track/'),
        #'delete': dbconfig.get('chirpapi.url.delete','http://192.168.58.128:8101/api/track/'),
        'create': dbconfig.get('chirpapi.url.create','http://geoff.terrorware.com/hacks/chirpapi/playlist/create'),
        'delete': dbconfig.get('chirpapi.url.delete','http://geoff.terrorware.com/hacks/chirpapi/playlist/delete')
    }
    return urls[type]


"""Helper funcs used by playlists.views
"""
def url_track_create(track):
    if in_dev():
        _url_track_create(track)
    else:
        taskqueue.add(url='/playlists/task_create', params={'id':str(track.key())})

def url_track_delete(key):
    if in_dev():
        _url_track_delete(key)
    else:
        taskqueue.add(url='/playlists/task_delete', params={'id':key})



""" bluk of the remoting code
"""
def _url_track_create(track=None):
    if track is None:
        return

    def as_utf8_str(s):
        if isinstance(s, unicode):
            s = s.encode('utf8')
        return s
    
    qs = {
        'track_name': as_utf8_str(track.track_title),
        'track_artist': as_utf8_str(track.artist_name),
        'dj_name': as_utf8_str("%s %s" % (track.selector.first_name, track.selector.last_name)),
        'time_played': track.modified.strftime("%Y-%m-%d %H:%M:%S"),
        'track_id': str(track.key()),
    }
    # optional:
    if track.album_title:
        qs['track_album'] = as_utf8_str(track.album_title)
    if track.label:
        qs['track_label'] = as_utf8_str(track.label)
    # TODO(kumar) waiting until API supports this:
    # if track.notes:
    #     qs['track_notes'] = as_utf8_str(track.notes)

    data = urllib.urlencode(qs)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    #
    url = _urls('create')
    #_fetch_url(url, data, 'POST', headers)
    _fetch_url(url, data, 'POST', headers, 'digest', url)

def _url_track_delete(id):
    if not id:
        return
    #
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    #
    url = _urls('delete')
    #_fetch_url(url + str(id), {}, 'DELETE', headers)
    _fetch_url(url + "/" + str(id), {}, 'DELETE', headers, 'digest', url)


"""urllib2.Request only supports GET|POST, extend it to support any HTTP method type
"""

class AnyRequest(urllib2.Request):

    def get_method(self):
        if hasattr(self, 'http_method'):
            return getattr(self, 'http_method')
        else:
            return urllib2.Request.get_method(self)

def _fetch_url(url=None, data=None, method='GET', headers=None, auth_type=None, auth_url=None):

    # init auth hander if using http authentication
    if auth_type and auth_type in ('basic','digest'):
        _auth_handler(CHIRPAPI_USERNAME, CHIRPAPI_PASSWORD, auth_type, auth_url)

    try:
        # request
        req = AnyRequest(url, data, headers)
        req.http_method = method

        # response
        res = urllib2.urlopen(req)
        d = {'code': res.code, 'content': res.read()}
        logging.info(d)
        return d
    except Exception, e:
        logging.error(e)
        pass

    return {}

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
def _get_track(key):
    return PlaylistEvent.get(key)

def task_create(request):
    _url_track_create(_get_track(request.POST['id']))

def task_delete(request):
    _url_track_delete(request.POST['id'])


"""WSGI Application  mapped in app.yaml
Since want to restrict access to appengine tasks need to set a handler
in app.yaml with 'login: admin' and script app handler tasks.py
taskqueue urls only use HTTP POST and have to be manually excuted
check admin console at http://HOST:PORT/_ah/admin/tasks?queue=default
"""
class TaskCreateHandler(webapp.RequestHandler):
    def post(self):
        _url_track_create(_get_track(self.request.get('id')))

class TaskDeleteHandler(webapp.RequestHandler):
    def post(self):
        _url_track_delete(self.request.get('id'))

def main():
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([
        ('/playlists/task_create', TaskCreateHandler),
        ('/playlists/task_delete', TaskDeleteHandler),
    ]))

if __name__ == '__main__':
    main()
