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

"""Views for the DJ Database."""

from functools import partial
import logging
import re

from google.appengine.api import datastore_errors, memcache
from google.appengine.ext import db
from django import forms
from django import http
from django.template import loader, Context, RequestContext

from auth.decorators import require_role
from auth import roles
from common import dbconfig, sanitize_html, pager
from common.autoretry import AutoRetry
from common.time_util import chicago_now
from common.utilities import as_json
from djdb import models
from djdb import search
from djdb import review
from djdb import comment
from djdb import forms
from djdb.models import Album
from playlists.models import ChirpBroadcast, PlaylistEvent, PlaylistTrack
from playlists.views import PlaylistEventView
from datetime import datetime, timedelta
import djdb.pylast as pylast
import random
import re
import tag_util

LAST_PLAYED_HOURS = 3
LAST_PLAYED_SECONDS = LAST_PLAYED_HOURS * 3600

log = logging.getLogger(__name__)

def fetch_activity(num=None, start_dt=None, days=None):
    default_num = 10
    activity = []
    
    # Get recent reviews.
    if num is None:
        num_reviews = default_num
    else:
        num_reviews = num
    revs = review.fetch_recent(num_reviews, start_dt=start_dt, days=days)
    for rev in revs:
        dt = rev.created_display.strftime('%Y-%m-%d %H:%M')
        if len(rev.text) > 100:
            text = rev.text[0:100] + '... <a href="%s">Read more</a>' % rev.subject.url
        else:
            text = rev.text
        item = '<a href="%s">%s / %s</a> <b>reviewed</b> by ' % (rev.subject.url, rev.subject.artist_name, rev.subject.title)
        if rev.author:
            item += '<a href="/djdb/user/%s">%s</a>.' % (rev.author.key().id(), rev.author_display)
        else:
            item += rev.author_display
        item += """
<blockquote>
%s
</blockquote>
            """ % text
        activity.append((dt, 'review', item))
            
    # Get recent comments.
    if num is None or len(activity) < num:
        if num is None:
            num_comments = default_num
        else:
            num_comments = num - len(activity)        
        comments = comment.fetch_recent(num_comments, start_dt=start_dt, days=days)
        for com in comments:
            dt = com.created_display.strftime('%Y-%m-%d %H:%M')
            if len(com.text) > 100:
                text = com.text[0:100] + '... <a href="%s">Read more</a>' % com.subject.url
            else:
                text = com.text
            item = '<a href="%s">%s / %s</a> <b>commented</b> on by ' % (com.subject.url, com.subject.artist_name, com.subject.title)
            if com.author:
                item += '<a href="/djdb/user/%s">%s</a>.' % (com.author.key().id(), com.author_display)
            else:
                item += com.author_display
            item += """
    <blockquote>
    %s
    </blockquote>
                """ % text
            activity.append((dt, 'comment', item))
    
    # Get recent tag edits.
    if num is None or len(activity) < num:
        if num is None:
            num_tags = default_num
        else:
            num_tags = num - len(activity)
        tag_edits = tag_util.fetch_recent(num_tags, start_dt=start_dt, days=days)
        for tag_edit in tag_edits:
            dt = tag_edit.timestamp_display.strftime('%Y-%m-%d %H:%M')
            for tag in tag_edit.added:
                if tag_edit.subject.kind() == 'Album':
                    if tag == 'recommended':                    
                        item = '<a href="%s">%s / %s / %s</a> <b>recommended</b> by <a href="/djdb/user/%s">%s</a>.' % (
                            tag_edit.subject.album.url, tag_edit.subject.album.artist_name,
                            tag_edit.subject.album.title, tag_edit.subject.title,
                            tag_edit.author.key().id(), tag_edit.author)
                        type = 'recommended'
                    elif tag == 'explicit':
                        item = '<a href="%s">%s / %s / %s</a> <b>marked explicit</b> by <a href="/djdb/user/%s">%s</a>.' % (
                            tag_edit.subject.album.url, tag_edit.subject.album.artist_name,
                            tag_edit.subject.album.title, tag_edit.subject.title,
                            tag_edit.author.key().id(), tag_edit.author)
                        type = 'explicit'
                    else:
                        item = '<a href="%s">%s / %s</a> <b>tagged</b> as <b>%s</b> by <a href="/djdb/user/%s">%s</a>.' % (
                            tag_edit.subject.url, tag_edit.subject.artist_name,
                            tag_edit.subject.title, tag, tag_edit.author.key().id(),
                            tag_edit.author)
                        type = 'tag'                    
                    activity.append((dt, type, item))
                
                for tag in tag_edit.removed:
                    if tag == 'recommended':
                        item = '<a href="%s">%s / %s / %s</a> <b>unrecommended</b> by <a href="/djdb/user/%s">%s</a>.' % (
                            tag_edit.subject.album.url, tag_edit.subject.album.artist_name,
                            tag_edit.subject.album.title, tag_edit.subject.title,
                            tag_edit.author.key().id(), tag_edit.author)
                        type = 'unrecommended'
                    elif tag == 'explicit':
                        item = '<a href="%s">%s / %s / %s</a> <b>ummarked explicit</b> by <a href="/djdb/user/%s">%s</a>.' % (
                            tag_edit.subject.album.url, tag_edit.subject.album.artist_name,
                            tag_edit.subject.album.title, tag_edit.subject.title,
                            tag_edit.author.key().id(), tag_edit.author)
                        type = 'unexplicit'
                    else:
                        item = '<a href="%s">%s / %s</a> <b>untagged</b> as <b>%s</b> by <a href="/djdb/user/%s">%s</a>.' % (
                            tag_edit.subject.url, tag_edit.subject.artist_name,
                            tag_edit.subject.title, tag, tag_edit.author.key().id(),
                            tag_edit.author)
                        type = 'untag'
                    activity.append((dt, type, item))
    
    # Sort activity list in place.
    activity.sort(reverse=True)
        
    # Prepare a list for the template.
    activity_list = []
    prev_dt = None
    lst = []
    for dt, type, item in activity:
        if prev_dt and dt != prev_dt and lst:
            activity_list.append((datetime.strptime(dt, '%Y-%m-%d %H:%M'), lst))
            lst = []
        lst.append((type, item))
        prev_dt = dt
    if lst:
        activity_list.append((datetime.strptime(dt, '%Y-%m-%d %H:%M'), lst))
    
    return activity_list
    
def landing_page(request, ctx_vars=None):
    template = loader.get_template('djdb/landing_page.html')
    if ctx_vars is None : ctx_vars = {}
    ctx_vars['title'] = 'DJ Database'

    # Fetch recent activity.
    days = 5
    start_dt = datetime.now() - timedelta(days=days)
    ctx_vars["recent_activity"] = fetch_activity(10, start_dt, days)

    if request.method == "POST":
        query_str = request.POST.get("query")
        reviewed = request.POST.get("reviewed")
        user_key = request.POST.get("user_key")
    else:
        query_str = request.GET.get("query")
        reviewed = request.GET.get("reviewed")
        user_key = request.GET.get("user_key")

    if query_str:
        ctx_vars["query_str"] = query_str
        if reviewed is None:
            reviewed = False
        else:
            reviewed = True
        if request.user.is_music_director:
            include_revoked = True
        else:
            include_revoked = False
        matches = search.simple_music_search(query_str, reviewed=reviewed,
                                             user_key=user_key,
                                             include_revoked=include_revoked)
        if matches is None:
            ctx_vars["invalid_query"] = True
        else:
            ctx_vars["query_results"] = matches
    elif reviewed and user_key:
        return http.HttpResponseRedirect("/djdb/reviews?author_key=%s" % user_key)

    # Add categories.
    ctx_vars["categories"] = models.ALBUM_CATEGORIES
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def activity_page(request, ctx_vars=None):
    template = loader.get_template('djdb/activity.html')
    if ctx_vars is None:
        ctx_vars = {}
    ctx_vars['title'] = 'DJ Database Activity'
    
    now = datetime.now().replace(hour=0, minute=0, second=0,
                                 microsecond=0)
    if request.method == 'GET':
        form = forms.ListActivityForm({'from_month': now.month,
                                       'from_day': now.day,
                                       'from_year': now.year})
        start_dt = now
    else:
        if request.POST.get('search'):
            form = forms.ListActivityForm(request.POST)
            if form.is_valid():
                from_month = int(form.cleaned_data['from_month'])
                from_day = int(form.cleaned_data['from_day'])
                from_year = int(form.cleaned_data['from_year'])
                start_dt = datetime(from_year, from_month, from_day)
        else:
            old_start_dt = request.POST.get('start_dt')
            if request.POST.get('next'):
                start_dt = datetime.strptime(old_start_dt, '%Y-%m-%d') \
                    - timedelta(days=1)
            else:
                start_dt = datetime.strptime(old_start_dt, '%Y-%m-%d') \
                    + timedelta(days=1)
                if start_dt > now:
                    start_dt = now
            form = forms.ListActivityForm({'from_month': start_dt.month,
                                           'from_day': start_dt.day,
                                           'from_year': start_dt.year})
    
    ctx_vars['form'] = form
    ctx_vars['start_dt'] = start_dt
    ctx_vars['recent_activity'] = fetch_activity(start_dt=start_dt, days=1)
            
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def reviews_page(request, ctx_vars=None): 
    default_page_size = 10
    default_order = 'created'
    
    template = loader.get_template('djdb/reviews.html')
    if ctx_vars is None : ctx_vars = {}
    ctx_vars['title'] = 'DJ Database Reviews'

    if request.method == "GET":
        form = forms.ListReviewsForm()
        author_key = request.GET.get('author_key')
        page_size = default_page_size
        order = default_order
        bookmark = None
    else:
        page_size = int(request.POST.get('page_size', default_page_size))
        form = forms.ListReviewsForm(request.POST)
        if form.is_valid():
            author_key = request.POST.get('author_key')
            order = request.POST.get('order')
            bookmark = request.POST.get('bookmark')
    if order not in ['created', 'author']:
        return http.HttpResponse(status=404)
    query = pager.PagerQuery(models.Document).filter("doctype =", models.DOCTYPE_REVIEW).filter("revoked =", False)
    if author_key:
        author = db.get(author_key)
        query.filter('author =', author)
    query.order("-%s" % order)
    prev, reviews, next = query.fetch(page_size, bookmark)
    ctx_vars["reviews"] = reviews
    ctx_vars["prev"] = prev
    ctx_vars["next"] = next
    ctx_vars["form"] = form
    ctx_vars["author_key"] = author_key
    ctx_vars["page_size"] = page_size
    ctx_vars["order"] = order
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def get_played_tracks(events):
    played_tracks = []
    prev_dt = None
    tracks = []
    for event in events:
        pl_view = PlaylistEventView(event)
        dt = pl_view.established_display.strftime('%Y-%m-%d %H')
        if prev_dt is not None and dt != prev_dt:
            played_tracks.append((datetime.strptime(prev_dt, '%Y-%m-%d %H'), tracks))
            tracks = []
        tracks.append(event)
        prev_dt = dt
    if tracks:
        played_tracks.append((datetime.strptime(dt, '%Y-%m-%d %H'), tracks))
    return played_tracks

def user_info_page(request, user_id, ctx_vars=None):
    if ctx_vars is None:
        ctx_vars = {}
    
    # Get user and check if exists and authorized.
    if user_id == '':
        if request.method == "POST":
            user_key = request.POST.get("user_key")
            if user_key == '':
                return http.HttpResponse(status=404)
            user = db.get(request.POST.get("user_key"))
            if user is None:
                return http.HttpResponse(status=404)
            return http.HttpResponseRedirect('/djdb/user/%d' % user.key().id())
        else:
            user = None
            ctx_vars["title"] = 'Find a DJ'
    else:
        user = models.User.get_by_id(int(user_id))
        if user is None or (not user.is_superuser and roles.DJ not in user.roles):
            return http.HttpResponse(status=404)

    if user is not None:
        query = PlaylistEvent.all().filter("playlist =", ChirpBroadcast()) \
                                   .filter("selector =", user).order("-established")
        ctx_vars["playlist_events"] = get_played_tracks(query.fetch(10))

        # Get reviews.
        query = models.Document.all().filter("doctype =", models.DOCTYPE_REVIEW) \
                                     .filter("revoked =", False) \
                                     .filter("author =", user) \
                                     .order("-created")
        ctx_vars["reviews"] = query.fetch(10)

        # Set page title.
        ctx_vars["title"] = user

    ctx_vars["dj"] = user

    # Return rendered page.
    template = loader.get_template('djdb/user_info_page.html')
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def tracks_played_page(request, user_id, ctx_vars=None): 
    default_page_size = 10
    default_month = 1
    default_day = 1
    default_year = 2009
    
    if ctx_vars is None:
        ctx_vars = {}
    ctx_vars['title'] = 'Tracks Played'

    user = models.User.get_by_id(int(user_id))
    if user is None or (not user.is_superuser and roles.DJ not in user.roles):
        return http.HttpResponse(status=404)

    if request.method == "GET":
        form = forms.ListTracksPlayedForm()
        page_size = default_page_size
        from_month = default_month
        from_day = default_day
        from_year = default_year
        bookmark = None
    else:
        page_size = int(request.POST.get('page_size', default_page_size))
        from_month = int(request.POST.get('from_month', default_month))
        from_day = int(request.POST.get('from_day', default_day))
        from_year = int(request.POST.get('from_year', default_year))
        form = forms.ListTracksPlayedForm(request.POST)
        if form.is_valid():
            order = request.POST.get('order')
            bookmark = request.POST.get('bookmark')
    dt = datetime(from_year, from_month, from_day, 0, 0, 0)
    query = pager.PagerQuery(PlaylistEvent).filter('playlist =', ChirpBroadcast()) \
                                           .filter('selector =', user.key()) \
                                           .filter('established >=', dt)
    query.order("-established")
    prev, events, next = query.fetch(page_size, bookmark)
    ctx_vars["playlist_events"] = get_played_tracks(events)
    ctx_vars["prev"] = prev
    ctx_vars["next"] = next
    ctx_vars["form"] = form
    ctx_vars["dj"] = user

    # Display page.
    ctx = RequestContext(request, ctx_vars)
    template = loader.get_template('djdb/tracks_played.html')
    return http.HttpResponse(template.render(ctx))

def artist_info_page(request, artist_name, ctx_vars=None):
    if request.user.is_music_director:
        include_revoked = True
    else:
        include_revoked = False

    artist = models.Artist.fetch_by_name(artist_name, include_revoked)
    if artist is None:
        return http.HttpResponse(status=404)
    template = loader.get_template("djdb/artist_info_page.html")
    if ctx_vars is None : ctx_vars = {}
    title = artist.pretty_name
    if request.user.is_music_director:
        title += ' <a href="" class="edit_artist"><img src="/media/common/img/page_white_edit.png"/></a>'
        if artist.revoked:
            title += ' <a href="/djdb/artist/%s/unrevoke" title="Unrevoke artist"><img src="/media/common/img/unrevoke_icon.png" alt="Unrevoke artist"/></a>' % artist.name
        else:
            title += ' <a href="/djdb/artist/%s/revoke" title="Revoke artist"><img src="/media/common/img/revoke_icon.png" alt="Revoke artist"/></a>' % artist.name

    ctx_vars["title"] = title
    ctx_vars["artist"] = artist
    if include_revoked:
        ctx_vars["albums"] = artist.sorted_albums_all
    else:
        ctx_vars["albums"] = artist.sorted_albums
    ctx_vars["categories"] = models.ALBUM_CATEGORIES

    if request.user.is_music_director:
        artist_form = None
        if request.method == "GET":
            artist_form = forms.PartialArtistForm({'pronunciation': artist.pronunciation})
        else:
            artist_form = forms.PartialArtistForm(request.POST)
            if artist_form.is_valid() and "update_artist" in request.POST:
                # Update artist and search index.
                idx = search.Indexer(artist.parent_key())
                idx.update_artist(artist, {"pronunciation" : artist_form.cleaned_data["pronunciation"]})
                idx.save()
        ctx_vars["artist_form"] = artist_form

    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def artist_search_for_autocomplete(request):
    matching_entities = _get_matches_for_partial_entity_search(
                                            request.GET.get('q', ''),
                                            'Artist')        
    response = http.HttpResponse(mimetype="text/plain")
    start_dt = datetime.now() - timedelta(seconds=LAST_PLAYED_SECONDS)
    for ent in matching_entities:
        # Check if track played recently. 
        query = PlaylistTrack.all().filter('playlist =', ChirpBroadcast()) \
                                   .filter('established >=', start_dt) \
                                   .filter('artist =', ent.key())
        if query.count() > 0:
            error = "Track from artist already played within the last %d hours." % LAST_PLAYED_HOURS
        else:
            error = ''
        response.write("%s|%s|%s\n" % (ent.pretty_name, ent.key(), error))
    return response

def album_search_for_autocomplete(request):
    matching_entities = _get_matches_for_partial_entity_search(
                                            request.GET.get('q', ''),
                                            'Album')        
    response = http.HttpResponse(mimetype="text/plain")
    unique_entities = set()
    start_dt = datetime.now() - timedelta(seconds=LAST_PLAYED_SECONDS)
    for ent in matching_entities:
        # Check if track played recently. 
        query = PlaylistTrack.all().filter('playlist =', ChirpBroadcast()) \
                                   .filter('established >=', start_dt) \
                                   .filter('album =', ent.key())
        if query.count() > 0:
            error = "Track from album already played within the last %d hours." % LAST_PLAYED_HOURS
        else:
            error = ''
        response.write("%s|%s|%s|%s\n" % (ent.title, ent.key(), ent.category, error))

    return response

def label_search_for_autocomplete(request):
    matching_entities = _get_matches_for_partial_entity_search(
                            'label:%s' % request.GET.get('q', ''),
                            'Album')
    response = http.HttpResponse(mimetype="text/plain")
    unique_labels = set()
    for ent in matching_entities:
        unique_labels.add(ent.label)
    for label in unique_labels:
        response.write("%s\n" % label)
    return response


_unsearchable_chars = re.compile(r'[^a-zA-Z ]')

def _searchable(s):
    """A search-friendly version of s without punctuation, etc."""
    return _unsearchable_chars.sub('', s).lower()


def _search_artist_tracks(artist=None, artist_key=None):
    assert artist or artist_key, 'Incorrect arguments'
    tracks = []
    ak = artist_key or artist.key()
    key = '_search_artist_tracks.%s' % ak
    try:
        cached = memcache.get(key)
    except:
        cached = None
        log.exception('getting from memcache')

    if cached:
        tracks = cached
    else:
        if not artist:
            artist = models.Artist.get(artist_key)
        albums = list(db.Query(models.Album, keys_only=True)
                      .filter('album_artist =', artist))
        q = models.Track.all().filter('album IN', albums).order('title')
        for t in q:
            tracks.append({'song': t.title,
                           'song_key': str(t.key()),
                           'song_tags': t.current_tags,
                           'album': t.album.title,
                           'album_key': str(t.album.key()),
                           'label': t.album.label})
        try:
            memcache.set(key, tracks, time=60 * 4)
        except:
            log.exception('setting memcache')
    return tracks


@as_json
def track_search(request):
    matches = []
    artists = []
    if request.GET.get('artist_key'):
        artists.append({'artist': request.GET['artist'],
                        'artist_key': request.GET['artist_key']})
    elif request.GET.get('artist'):
        if len(request.GET['artist']) >= 3:
            results = _get_matches_for_partial_entity_search(
                                                request.GET['artist'],
                                                'Artist')
            for artist in results:
                artists.append({'artist': artist.pretty_name,
                                'artist_key': str(artist.key()),
                                'artist_object': artist})
    if len(artists):
        if len(artists) == 1:
            artist = artists[0]
            kw = dict(artist=artist.get('artist_object'),
                      artist_key=artist.get('artist_key'))
            for data in _search_artist_tracks(**kw):
                d = {'artist': artist['artist'],
                     'artist_key': artist['artist_key'],
                     'song': data['song'],
                     'song_key': data['song_key'],
                     'song_tags': data['song_tags'],
                     'album': data['album'],
                     'album_key': data['album_key'],
                     'label': data['label']}
                if request.GET.get('song'):
                    # Do a substring search within tracks:
                    t = request.GET['song']
                    if _searchable(t) in _searchable(data['song']):
                        matches.append(d)
                else:
                    matches.append(d)

        for artist in artists:
            matches.append({'artist': artist['artist'],
                            'artist_key': artist['artist_key']})
    return {'matches': matches}


def _update_category(item, category, user):
    if category == models.CORE_TAG:
        if models.CORE_TAG in models.TagEdit.fetch_and_merge(item):
            tag_util.remove_tag_and_save(user, item, models.CORE_TAG)
        else:
            tag_util.add_tag_and_save(user, item, models.CORE_TAG)
    elif category == models.LOCAL_CURRENT_TAG:
        if models.LOCAL_CURRENT_TAG in models.TagEdit.fetch_and_merge(item):
            tag_util.remove_tag_and_save(user, item, models.LOCAL_CURRENT_TAG)
        else:
            tag_util.modify_tags_and_save(user, item,
                                          [models.LOCAL_CURRENT_TAG],
                                          [models.LOCAL_CLASSIC_TAG])
    elif category == models.LOCAL_CLASSIC_TAG:
        if models.LOCAL_CLASSIC_TAG in models.TagEdit.fetch_and_merge(item):
            tag_util.remove_tag_and_save(user, item, models.LOCAL_CLASSIC_TAG)
        else:
            tag_util.modify_tags_and_save(user, item,
                                          [models.LOCAL_CLASSIC_TAG],
                                          [models.LOCAL_CURRENT_TAG])
    elif category == models.HEAVY_ROTATION_TAG:
        if models.HEAVY_ROTATION_TAG in models.TagEdit.fetch_and_merge(item):
            tag_util.remove_tag_and_save(user, item, models.HEAVY_ROTATION_TAG)
        else:
            tag_util.modify_tags_and_save(user, item,
                                          [models.HEAVY_ROTATION_TAG],
                                          [models.LIGHT_ROTATION_TAG])
    elif category == models.LIGHT_ROTATION_TAG:
        if models.LIGHT_ROTATION_TAG in models.TagEdit.fetch_and_merge(item):
            tag_util.remove_tag_and_save(user, item, models.LIGHT_ROTATION_TAG)
        else:
            tag_util.modify_tags_and_save(user, item,
                                          [models.LIGHT_ROTATION_TAG],
                                          [models.HEAVY_ROTATION_TAG])

@require_role(roles.MUSIC_DIRECTOR)
def update_albums(request) :
    mark_as = request.POST.get('mark_as')
    for name in request.POST.keys() :
        if re.match('checkbox_', name) :
            type, num = name.split('_')
            album_key = request.POST.get('album_key_%s' % num)
            album = AutoRetry(Album).get(album_key)

            # Set album category.
            _update_category(album, mark_as, request.user)

            # Set track category.
            for track in album.track_set:
                _update_category(track, mark_as, request.user)

            # Set album categories.
            album_categories = set()
            for album in album.album_artist.album_set:
                for tag in album.current_tags:
                    if tag in models.ALBUM_CATEGORIES:
                        album_categories.add(tag)
            tag_util.set_tags_and_save(request.user, album.album_artist, album_categories)

    if request.POST.get('response_page') == 'artist' :
        return artist_info_page(request, request.POST.get('artist_name'))
    else :
        return landing_page(request)

@require_role(roles.MUSIC_DIRECTOR)
def artist_revoke(request, artist_name):
    artist = models.Artist.fetch_by_name(artist_name)
    if artist is None:
        return http.HttpResponse(status=404)

    artist.revoked = True
    AutoRetry(artist).save()

    for album in artist.album_set:
        album.revoked = True
        AutoRetry(album).save()
        for track in album.track_set:
            track.revoked = True
            AutoRetry(track).save()

    ctx_vars = {}    
    response_page = request.GET.get('response_page')
    if response_page == 'landing':
        return http.HttpResponseRedirect('/djdb?query=%s' % request.GET.get('query'))
    elif response_page == 'browse':
        start_char = request.GET.get('start_char')
        page_size = request.GET.get('page_size')
        category = request.GET.get('category')
        bookmark = request.GET.get('bookmark')
        url = '/djdb/browse/artist/%s?' % start_char
        if page_size is not None:
            url += '&page_size=%s' % page_size
        if category is not None:
            url += '&category=%s' % category
        if bookmark is not None:
            url += '&bookmark=%s' % bookmark
        return http.HttpResponseRedirect(url)
    else:
        return http.HttpResponseRedirect('/djdb/artist/%s/info' % artist.name)

@require_role(roles.MUSIC_DIRECTOR)
def artist_unrevoke(request, artist_name):
    artist = models.Artist.fetch_by_name(artist_name, True)
    if artist is None:
        return http.HttpResponse(status=404)

    artist.revoked = False
    AutoRetry(artist).save()

    for album in artist.album_set:
        album.revoked = False
        AutoRetry(album).save()
        for track in album.track_set:
            track.revoked = False
            AutoRetry(track).save()

    ctx_vars = {}    
    response_page = request.GET.get('response_page')
    if response_page == 'landing':
        return http.HttpResponseRedirect('/djdb?query=%s' % request.GET.get('query'))
    elif response_page == 'browse':
        start_char = request.GET.get('start_char')
        page_size = request.GET.get('page_size')
        category = request.GET.get('category')
        bookmark = request.GET.get('bookmark')
        url = '/djdb/browse/artist/%s?' % start_char
        if page_size is not None:
            url += '&page_size=%s' % page_size
        if category is not None:
            url += '&category=%s' % category
        if bookmark is not None:
            url += '&bookmark=%s' % bookmark
        return http.HttpResponseRedirect(url)
    else:
        return http.HttpResponseRedirect('/djdb/artist/%s/info' % artist.name)

def _get_tag_or_404(tag_name):
    q = models.Tag.all().filter("name =", tag_name)
    tag = None
    for tag in AutoRetry(q).fetch(1):
        pass
    if tag is None:
        return http.HttpResponse(status=404)
    return tag

@require_role(roles.MUSIC_DIRECTOR)
def list_tags(request, tag_name=None):
    ctx_vars = {'title': 'Tags',
                'tags': models.Tag.all().order('name')}    
    ctx = RequestContext(request, ctx_vars)
    template = loader.get_template('djdb/tags.html')
    return http.HttpResponse(template.render(ctx))

@require_role(roles.MUSIC_DIRECTOR)
def new_tag(request):
    template = loader.get_template('djdb/tag_form.html')
    ctx_vars = {'title': 'New Tag',
                'new': True}
    
    if request.method == 'GET':
        ctx_vars['form'] = forms.TagForm()
    else:
        form = forms.TagForm(request.POST)
        ctx_vars['form'] = form
        if form.is_valid():
            # Check if already present.
            q = models.Tag.all().filter('name =', form.cleaned_data['name'])
            if len(q.fetch(1)) == 1:
                ctx_vars['error'] = 'Tag already exists.'
            else:
                tag = models.Tag(name=form.cleaned_data['name'],
                                 description=form.cleaned_data['description'])
                AutoRetry(db).put(tag)
                return http.HttpResponseRedirect('/djdb/tags')
        
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

@require_role(roles.MUSIC_DIRECTOR)
def edit_tag(request, tag_name):
    template = loader.get_template('djdb/tag_form.html')
    ctx_vars = {'title': 'Edit Tag',
                'edit': True}
    
    # Get tag.
    tag = _get_tag_or_404(tag_name)
    ctx_vars['tag'] = tag

    if request.method == 'GET':
        ctx_vars['form'] = forms.TagForm({'name': tag.name,
                                          'description': tag.description})
    else:
        form = forms.TagForm(request.POST)
        ctx_vars['form'] = form
        if form.is_valid():
            tag.name = form.cleaned_data['name']
            tag.description = form.cleaned_data['description']
            AutoRetry(tag).save()
            return http.HttpResponseRedirect('/djdb/tags')
        
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def album_add_tag(request, album_id_str):
    album = _get_album_or_404(album_id_str)
    tag_util.add_tag_and_save(request.user, album, request.GET.get('tag'), True)
    
def album_remove_tag(request, album_id_str):
    album = _get_album_or_404(album_id_str)
    tag_util.remove_tag_and_save(request.user, album, request.GET.get('tag'))
    return http.HttpResponse()

def update_tracks(request, album_id_str):
    album = _get_album_or_404(album_id_str)

    ctx_vars = {}

    # Update track information.
    if request.user.is_music_director:
        for name in request.POST.keys() :
            m = re.match('update_track_(\d+)', name)
            if m:
                track_num = m.group(1)
                pronunciation = request.POST.get("pronunciation_%s" % track_num)
                artist_key = request.POST.get("track_artist_key_%s" % track_num)
                if artist_key != "":
                    artist = db.get(artist_key)
                else:
                    artist = None
                track = db.get(request.POST.get("track_key_%s" % track_num))
                idx = search.Indexer(track.parent_key())
                idx.update_track(track, {"pronunciation": pronunciation,
                                         "track_artist" : artist})
                idx.save()
#                else:
#                    ctx_vars['error'] = 'Artist specified not in DJ database. Note, you must click one of the auto-complete entries.'
                break

    # Update track explicit and recommended tags.
    error = ''
    mark_as = request.POST.get('mark_as')
    for name in request.POST.keys() :
        if re.match('checkbox_', name) :
            type, num = name.split('_')
            track = album.sorted_tracks[int(num) - 1]
            if mark_as == 'explicit' :
                if models.EXPLICIT_TAG in models.TagEdit.fetch_and_merge(track) :
                    tag_util.remove_tag_and_save(request.user, track, models.EXPLICIT_TAG)
                else :
                    tag_util.modify_tags_and_save(request.user, track,
                                                  [models.EXPLICIT_TAG],
                                                  [models.RECOMMENDED_TAG])
            elif mark_as == 'recommended' :
                if models.EXPLICIT_TAG in models.TagEdit.fetch_and_merge(track):
                    error = 'Cannot recommend an explicit track.'
                else:
                    if models.RECOMMENDED_TAG in models.TagEdit.fetch_and_merge(track) :
                        tag_util.remove_tag_and_save(request.user, track, models.RECOMMENDED_TAG)
                    else :
                        tag_util.add_tag_and_save(request.user, track, models.RECOMMENDED_TAG)
    ctx_vars['error'] = error
    
    request.method = 'GET'            
    return album_info_page(request, album_id_str, ctx_vars)

@require_role(roles.MUSIC_DIRECTOR)
def track_revoke(request, track_key):
    track = db.get(track_key)
    if track:
        track.revoked = True
        AutoRetry(track).save()
    else:
        return http.HttpResponse(status=404)
    
    ctx_vars = {}    
    response_page = request.GET.get('response_page')
    if response_page == 'landing':
        return http.HttpResponseRedirect('/djdb?query=%s' % request.GET.get('query'))
    elif response_page == 'browse':
        start_char = request.GET.get('start_char')
        page_size = request.GET.get('page_size')
        category = request.GET.get('category')
        bookmark = request.GET.get('bookmark')
        url = '/djdb/browse/track/%s?' % start_char
        if page_size is not None:
            url += '&page_size=%s' % page_size
        if category is not None:
            url += '&category=%s' % category
        if bookmark is not None:
            url += '&bookmark=%s' % bookmark
        return http.HttpResponseRedirect(url)
    else:
        return http.HttpResponseRedirect('/djdb/album/%s/info' % track.album.album_id)

@require_role(roles.MUSIC_DIRECTOR)
def track_unrevoke(request, track_key):
    track = db.get(track_key)
    if track:
        track.revoked = False
        AutoRetry(track).save()
    else:
        return http.HttpResponse(status=404)
    
    ctx_vars = {}    
    response_page = request.GET.get('response_page')
    if response_page == 'landing':
        return http.HttpResponseRedirect('/djdb?query=%s' % request.GET.get('query'))
    elif response_page == 'browse':
        start_char = request.GET.get('start_char')
        page_size = request.GET.get('page_size')
        category = request.GET.get('category')
        bookmark = request.GET.get('bookmark')
        url = '/djdb/browse/track/%s?' % start_char
        if page_size is not None:
            url += '&page_size=%s' % page_size
        if category is not None:
            url += '&category=%s' % category
        if bookmark is not None:
            url += '&bookmark=%s' % bookmark
        return http.HttpResponseRedirect(url)
    else:
        return http.HttpResponseRedirect('/djdb/album/%s/info' % track.album.album_id)

def browse_page(request, entity_kind, start_char, ctx_vars=None):
    allowed = map(chr, range(65, 91))
    allowed.extend(['all', '0', 'other', 'random'])
    if start_char not in allowed:
        return http.HttpResponse(status=404)
    
    template = loader.get_template('djdb/browse_page.html')
    if ctx_vars is None : ctx_vars = {}
    ctx_vars["title"] = 'Browse DJ Database'
    ctx_vars["entity_kind"] = entity_kind
    ctx_vars["start_char"] = start_char
    ctx_vars["categories"] = models.ALBUM_CATEGORIES

    page_size = 10
    if request.method == "GET":
        reviewed = request.GET.get('reviewed')
        bookmark = request.GET.get('bookmark')
        category = request.GET.get('category')
        form = forms.BrowseForm(request.GET, entity_kind=entity_kind)
    else:
        reviewed = request.POST.get('reviewed')
        bookmark = request.POST.get('bookmark')
        category = request.POST.get('category')
        form = forms.BrowseForm(request.POST, entity_kind=entity_kind)

    if form.is_valid():
        if form.cleaned_data["page_size"]:
            page_size = int(form.cleaned_data["page_size"])
#        order = form.cleaned_data["order"]

    if start_char == "random" and entity_kind != "album":
        url = "/djdb/browse/%s/all?page_size=%d" % (entity_kind, page_size)
        if category is not None:
            url += "&category=%s" % category
        if reviewed is not None:
            url += "&reviewed=true"
        return http.HttpResponseRedirect(url)
    
    if category is not None and category not in models.ALBUM_CATEGORIES:
        return http.HttpResponse(status=404)
        
    if entity_kind == 'artist':
        model = models.Artist
        field = "name"
    elif entity_kind == 'album':
        model = models.Album
        field = "title"
    elif entity_kind == 'track':
        model = models.Track
        field = "title"
    else:
        return http.HttpResponse(status=404)

    if start_char == 'random':
        items = []
        query = models.Album.all().order('album_id')
        if reviewed is not None:
            query.filter('is_reviewed =', True)
        if category is not None:
            query.filter("current_tags =", category)
        alb = query.fetch(1)
        if len(alb) > 0:
            min = alb[0].album_id

            query = models.Album.all().order('-album_id')
            if reviewed is not None:
                query.filter('is_reviewed =', True)
            if category is not None:
                query.filter("current_tags =", category)
            alb = query.fetch(1)
            max = alb[0].album_id

            if min == max:
                alb = models.Album.all().filter('album_id =', min).fetch(1)
                items.append(alb[0])
            else:
                for i in range(page_size):
                    r = random.randrange(min, max)
                    # TODO(trow): Hopefully revoked albums will be rare.
                    query = models.Album.all().order('album_id') \
                                              .filter('album_id >=', r)
                    if reviewed is not None:
                        query.filter('is_reviewed =', True)
                    if category is not None:
                        query.filter("current_tags =", category)
                    for alb in query.fetch(20):        
                        if not alb.revoked:
                            items.append(alb)
                            break
        prev = None
        next = None
    else:
        query = pager.PagerQuery(model)
        if start_char == '0':
            query.filter("%s >=" % field, "0")
            query.filter("%s <" % field, u"9" + u"\uffff")
        elif start_char == 'other':
            query.filter("%s >=" % field, u"\u0021")
            query.filter("%s <" % field, u"\u0030")
        elif start_char != 'all':
            query.filter("%s >=" % field, start_char)
            query.filter("%s <" % field, start_char + u"\uffff")
        if category is not None:
            query.filter("current_tags =", category)
        if reviewed is not None:
            query.filter("is_reviewed =", True)
        if not request.user.is_music_director:
            query.filter("revoked =", False)
        query.order(field)
        prev, items, next = query.fetch(page_size, bookmark)
    
    ctx_vars["form"] = form
    ctx_vars["bookmark"] = bookmark
    ctx_vars["items"] = items
    ctx_vars["prev"] = prev
    ctx_vars["next"] = next
    ctx_vars["page_size"] = page_size
    ctx_vars["page_sizes"] = [10, 25, 50, 100]
    ctx_vars["reviewed"] = reviewed
    ctx_vars["category"] = category

    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))
    
def category_page(request, category):
    query = models.Album.all().filter("category =", category)
    albums = AutoRetry(query).fetch(AutoRetry(query).count())
    template = loader.get_template("djdb/category_page.html")
    ctx_vars = { "category": category,
                 "user": request.user,
                 "albums": albums }
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def track_search_for_autocomplete(request):
    matching_entities = _get_matches_for_partial_entity_search(
                                            request.GET.get('q', ''),
                                            'Track')
    artist_key = request.GET.get('artist_key', None)
    
    response = http.HttpResponse(mimetype="text/plain")
    start_dt = datetime.now() - timedelta(seconds=LAST_PLAYED_SECONDS)
    for track in matching_entities:
        if artist_key:
            # skip this track if it doesn't match the 
            # artist we are searching tracks by.
            # if a track doesn't have an associated artist 
            # then we will never filter it out.
            track_artist_key = None
            if track.track_artist:
                # for compilations
                track_artist_key = track.track_artist.key()
            if track.album:
                track_artist_key = track.album.album_artist.key()
            if track_artist_key:
                if str(track_artist_key) != str(artist_key):
                    continue

        # Check if track played recently. 
        query = PlaylistTrack.all().filter('playlist =', ChirpBroadcast()) \
                                   .filter('established >=', start_dt) \
                                   .filter('track =', track.key())
        if query.count() > 0:
            error = "Track already played within the last %d hours." % LAST_PLAYED_HOURS
        else:
            error = ''

        response.write("%s|%s|%s|%s\n" % (track.title, track.key(), track.album.category, error))
    return response

def _get_matches_for_partial_entity_search(query, entity_kind):
    if not query:
        return []
    if len(query) < 3:
        # conserve resources and refuse to perform a keyword 
        # search if query is less than 3 characters.
        return []
    # If the query string doesn't end in whitespace,
    # append star to match partial artist names.
    #       e.g. ?q=metalli will become "metalli*" to match Metallica
    if not query[-1].isspace():
        query = "%s*" % query
    matches = search.simple_music_search(query, max_num_results=25,
                                         entity_kind=entity_kind)
    if matches:
        return matches.get(entity_kind, [])
    else:
        return []

def _get_album_or_404(album_id_str):
    if not album_id_str.isdigit():
        return http.HttpResponse(status=404)
    q = models.Album.all().filter("album_id =", int(album_id_str))
    album = None
    for album in AutoRetry(q):
        if not album.revoked:
            break
    if album is None:
        return http.HttpResponse(status=404)
    return album

def album_info_page(request, album_id_str, ctx_vars=None):
    album = _get_album_or_404(album_id_str)
    template = loader.get_template("djdb/album_info_page.html")

    if ctx_vars is None:
        ctx_vars = {}

    try:
        lastfm = pylast.get_lastfm_network(api_key=dbconfig['lastfm.api_key'])
        lastfm_album = lastfm.get_album(album.artist_name, album.title)
        ctx_vars["album_cover_m"] = lastfm_album.get_cover_image(pylast.COVER_MEDIUM)
        ctx_vars["album_cover_xl"] = lastfm_album.get_cover_image(pylast.COVER_EXTRA_LARGE)
    except:
        ctx_vars["album_cover_m"] = "/media/common/img/no_cover_art.png"
        ctx_vars["album_cover_xl"] = "/media/common/img/no_cover_art.png"
        pass

    ctx_vars["album"] = album
    ctx_vars["album_tags"] = []
    for tag in models.Tag.all().order('name'):
        if tag.name not in album.current_tags:
            ctx_vars["album_tags"].append(tag.name)
    if request.user.is_music_director:
        ctx_vars["tracks"] = album.sorted_tracks_all
    else:
        ctx_vars["tracks"] = album.sorted_tracks
    ctx_vars["user"] = request.user
            
    if request.user.is_music_director:
        album_form = None
        if request.method == "GET":
            album_form = forms.PartialAlbumForm({'pronunciation': album.pronunciation,
                                                 'label': album.label,
                                                 'year': album.year,
                                                 'is_compilation': album.is_compilation,
                                                 'is_heavy_rotation': album.has_tag(models.HEAVY_ROTATION_TAG),
                                                 'is_light_rotation': album.has_tag(models.LIGHT_ROTATION_TAG),
                                                 'is_local_classic': album.has_tag(models.LOCAL_CLASSIC_TAG),
                                                 'is_local_current': album.has_tag(models.LOCAL_CURRENT_TAG)})
        else:
            album_form = forms.PartialAlbumForm(request.POST)
            if album_form.is_valid() and "update_album" in request.POST:
                # Update album and search index.
                idx = search.Indexer(album.parent_key())
                idx.update_album(album, {"pronunciation" : album_form.cleaned_data["pronunciation"],
                                         "label" : album_form.cleaned_data["label"],
                                         "year" : album_form.cleaned_data["year"],
                                         "is_compilation" : album_form.cleaned_data["is_compilation"]})
                idx.save()

                if album_form.cleaned_data["is_heavy_rotation"] != album.has_tag(models.HEAVY_ROTATION_TAG):
                    _update_category(album, models.HEAVY_ROTATION_TAG, request.user)
                if album_form.cleaned_data["is_light_rotation"] != album.has_tag(models.LIGHT_ROTATION_TAG):
                    _update_category(album, models.LIGHT_ROTATION_TAG, request.user)
                if album_form.cleaned_data["is_local_classic"] != album.has_tag(models.LOCAL_CLASSIC_TAG):
                    _update_category(album, models.LOCAL_CLASSIC_TAG, request.user)
                if album_form.cleaned_data["is_local_current"] != album.has_tag(models.LOCAL_CURRENT_TAG):
                    _update_category(album, models.LOCAL_CURRENT_TAG, request.user)
                AutoRetry(db).put(album)
        ctx_vars["album_form"] = album_form
    
    label = album.label
    if label is None:
        label = ''
    year = album.year
    if year is None:
        year = ''

    title = u'<a href="%s">%s</a> / %s / %s / %s' \
      % (album.artist_url, album.artist_name, album, label, str(year))
    if request.user.is_music_director:
        title += ' <a href="" class="edit_album"><img src="/media/common/img/page_white_edit.png"/></a>'
        if not album.is_compilation and not album.album_artist.revoked:
            if album.revoked:
                title += ' <a href="/djdb/album/%s/unrevoke" title="Unrevoke album"><img src="/media/common/img/unrevoke_icon.png" alt="Unrevoke album"/></a>' % album.album_id
            else:
                title += ' <a href="/djdb/album/%s/revoke" title="Revoke album"><img src="/media/common/img/revoke_icon.png" alt="Revoke album"/></a>' % album.album_id
    ctx_vars["title"] = title
    ctx_vars["show_reviews"] = album.reviews or request.user.is_music_director or request.user.is_reviewer
    ctx_vars["show_review_link"] = request.user.is_music_director or request.user.is_reviewer
    ctx_vars["show_album_tags"] = request.user.is_music_director or bool(album.sorted_current_tags)

    ctx_vars["album_categories"] = models.ALBUM_CATEGORIES
    for tag in models.ALBUM_CATEGORIES:
        if tag in album.current_tags:
            ctx_vars["has_category"] = True
            break

    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

@require_role(roles.MUSIC_DIRECTOR)
def album_revoke(request, album_id_str):
    album = _get_album_or_404(album_id_str)

    album.revoked = True
    AutoRetry(album).save()

    for track in album.track_set:
        track.revoked = True
        AutoRetry(track).save()

    ctx_vars = {}    
    response_page = request.GET.get('response_page')
    if response_page == 'landing':
        return http.HttpResponseRedirect('/djdb?query=%s' % request.GET.get('query'))
    elif response_page == 'artist':
        return http.HttpResponseRedirect('/djdb/artist/%s/info/' % album.album_artist.name)
    elif response_page == 'browse':
        start_char = request.GET.get('start_char')
        page_size = request.GET.get('page_size')
        category = request.GET.get('category')
        bookmark = request.GET.get('bookmark')
        url = '/djdb/browse/album/%s?' % start_char
        if page_size is not None:
            url += '&page_size=%s' % page_size
        if category is not None:
            url += '&category=%s' % category
        if bookmark is not None:
            url += '&bookmark=%s' % bookmark
        return http.HttpResponseRedirect(url)
    else:
        return http.HttpResponseRedirect('/djdb/album/%s/info' % album_id_str)

@require_role(roles.MUSIC_DIRECTOR)
def album_unrevoke(request, album_id_str):
    album = _get_album_or_404(album_id_str)

    album.revoked = False
    AutoRetry(album).save()

    for track in album.track_set:
        track.revoked = False
        AutoRetry(track).save()

    ctx_vars = {}    
    response_page = request.GET.get('response_page')
    if response_page == 'landing':
        return http.HttpResponseRedirect('/djdb?query=%s' % request.GET.get('query'))
    elif response_page == 'artist':
        return http.HttpResponseRedirect('/djdb/artist/%s/info/' % album.album_artist.name)
    elif response_page == 'browse':
        start_char = request.GET.get('start_char')
        page_size = request.GET.get('page_size')
        category = request.GET.get('category')
        bookmark = request.GET.get('bookmark')
        url = '/djdb/browse/album/%s?' % start_char
        if page_size is not None:
            url += '&page_size=%s' % page_size
        if category is not None:
            url += '&category=%s' % category
        if bookmark is not None:
            url += '&bookmark=%s' % bookmark
        return http.HttpResponseRedirect(url)
    else:
        return http.HttpResponseRedirect('/djdb/album/%s/info' % album_id_str)

def album_edit_review(request, album_id_str, review_key=None):
    album = _get_album_or_404(album_id_str)
    template = loader.get_template("djdb/album_edit_review.html")
    ctx_vars = { "album": album,
                 "valid_html_tags": sanitize_html.valid_tags_description() }
    if review_key:
        doc = review.get_or_404(review_key)
        ctx_vars["review"] = doc
        if doc.author:
            ctx_vars['author_key'] = doc.author.key()
        ctx_vars["title"] = "Edit Review"
        ctx_vars["edit"] = True
    else:
        ctx_vars["title"] = "New Review"

    form = None
    if request.method == "GET":
        attrs = None
        initial = None
        if review_key:
            attrs = {'text': doc.text}
            if request.user.is_music_director or request.user.is_reviewer:
                attrs['author'] = doc.author_display
                attrs['label'] = doc.subject.label
                attrs['year'] = doc.subject.year
        else:
            initial = {'label': album.label,
                       'year': album.year}
        form = review.Form(request.user, attrs, initial=initial)
    else:
        form = review.Form(request.user, request.POST)
        if form.is_valid():
            if "preview" in request.POST:
                ctx_vars["preview"] = sanitize_html.sanitize_html(
                    form.cleaned_data["text"])
                if request.user.is_music_director or request.user.is_reviewer:
                    if request.POST.get('author'):
                        ctx_vars["author_key"] = request.POST.get("author_key")
                        ctx_vars["author_name"] = request.POST.get("author")
                    else:
                        ctx_vars["author_key"] = request.user.key()
                        ctx_vars["author_name"] = request.user
                    ctx_vars["label"] = request.POST.get("label")
                    ctx_vars["year"] = request.POST.get("year")
                ctx_vars["tags"] = request.POST.getlist("tags[]")
            elif "save" in request.POST:
                if request.POST.get('author_key'):
                    author = AutoRetry(db).get(request.POST.get('author_key'))
                else:
                    author_name = request.POST.get('author')
                    first_name, sep, last_name = author_name.partition(' ')
                    query = models.User.all()
                    query.filter("first_name =", first_name)
                    query.filter("last_name =", last_name)
                    author = AutoRetry(query).fetch(1)
                    if author: author = author[0]

                # Save author or author name.
                if author:
                    if review_key:
                        doc.author = author
                        doc.author_name = None
                    else:
                        doc = review.new(album, user=author)
                else:
                    if review_key:
                        doc.author = None
                        doc.author_name = author_name
                    else:
                        doc = review.new(album, user_name=author_name)
                
                doc.unsafe_text = form.cleaned_data["text"]
                
                if review_key:
                    AutoRetry(doc).save()
                else:
                    items = [album, doc]

                    # Increment the number of reviews.
                    album.num_reviews += 1
                    album.is_reviewed = True

                    # Update tracks.
                    for track in album.track_set:
                        track.is_reviewed = True
                        items.append(track)

                    # Update artist.
                    if not album.is_compilation:
                        album.album_artist.is_reviewed = True
                        items.append(album.album_artist)

                    # Now save both the modified album and the document.
                    # They are both in the same entity group, so this write
                    # is atomic.
                    AutoRetry(db).put(items)
                
                # Update album info.
                if request.user.is_music_director or request.user.is_reviewer:
                    idx = search.Indexer(album.parent_key())
                    idx.update_album(album, {"label" : form.cleaned_data["label"],
                                             "year" : form.cleaned_data["year"]})
                    idx.save()

                # Redirect back to the album info page.
                return http.HttpResponseRedirect(album.url)
    ctx_vars["form"] = form
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

@require_role(roles.MUSIC_DIRECTOR)
def album_hide_unhide_review(request, album_id_str, review_key):
    album = _get_album_or_404(album_id_str)
    doc = review.get_or_404(review_key)
    if doc.is_hidden:
        doc.is_hidden = False
    else:
        doc.is_hidden = True
    AutoRetry(doc).save()
    return album_info_page(request, album_id_str)

@require_role(roles.MUSIC_DIRECTOR)
def album_delete_review(request, album_id_str, review_key=None):
    album = _get_album_or_404(album_id_str)
    if review_key is None:
        review_key = request.POST.get('review_key')
    doc = review.get_or_404(review_key)
    if request.POST.get('confirm'):
        AutoRetry(doc).delete()
        album.num_reviews -= 1
        AutoRetry(album).save()
    return album_info_page(request, album_id_str)
    
def album_edit_comment(request, album_id_str, comment_key=None):
    album = _get_album_or_404(album_id_str)
    template = loader.get_template("djdb/album_edit_comment.html")
    ctx_vars = { "album": album,
                 "valid_html_tags": sanitize_html.valid_tags_description() }
    if comment_key:
        doc = comment.get_or_404(comment_key)
        ctx_vars["comment"] = doc
        ctx_vars["title"] = "Edit Comment"
        ctx_vars["edit"] = True
    else:
        ctx_vars["title"] = "New Comment"

    form = None
    if request.method == "GET":
        attrs = None
        if comment_key:
            attrs = {'text': doc.text}
        form = comment.Form(attrs)
    else:
        form = comment.Form(request.POST)
        if form.is_valid():
            if "preview" in request.POST:
                ctx_vars["preview"] = sanitize_html.sanitize_html(
                    form.cleaned_data["text"])
            elif "save" in request.POST:
                if comment_key is None:
                    doc = comment.new(album, request.user)
                doc.unsafe_text = form.cleaned_data["text"]
                if comment_key:
                    AutoRetry(doc).save()
                else:
                    doc.unsafe_text = form.cleaned_data["text"]
                    # Increment the number of commentss.
                    album.num_comments += 1
                    # Now save both the modified album and the document.
                    # They are both in the same entity group, so this write
                    # is atomic.
                    AutoRetry(db).put([album, doc])
                # Redirect back to the album info page.
                return http.HttpResponseRedirect(album.url)
    ctx_vars["form"] = form
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

@require_role(roles.MUSIC_DIRECTOR)
def album_hide_unhide_comment(request, album_id_str, comment_key):
    album = _get_album_or_404(album_id_str)
    doc = comment.get_or_404(comment_key)
    if doc.is_hidden:
        doc.is_hidden = False
    else:
        doc.is_hidden = True
    AutoRetry(doc).save()
    return album_info_page(request, album_id_str)

@require_role(roles.MUSIC_DIRECTOR)
def album_delete_comment(request, album_id_str, comment_key=None):
    album = _get_album_or_404(album_id_str)
    if comment_key is None:
        comment_key = request.POST.get('comment_key')
    doc = comment.get_or_404(comment_key)
    if request.POST.get('confirm'):
        AutoRetry(doc).delete()
        album.num_comments -= 1
        AutoRetry(album).save()
    return album_info_page(request, album_id_str)

def image(request):
    img = models.DjDbImage.get_by_url(request.path)
    if img is None:
        return http.HttpResponse(status=404)
    return http.HttpResponse(content=img.image_data,
                             mimetype=img.image_mimetype)

def _get_crate(user, crate_key=None):
    # Get default crate.
    if crate_key is None:
        crates = AutoRetry(models.Crate.all().filter("user =", user) \
                                             .filter("is_default =", True)).fetch(1)

        # If no default crate, use the first one or create a new one.
        if len(crates) == 0:
            crates = AutoRetry(models.Crate.all().filter("user =", user)).fetch(999)
            
            # If no crates, create one.
            if len(crates) == 0:
                crate = models.Crate(user=user, is_default=True)
                AutoRetry(db).put(crate)

            # Make the first one default.            
            else:
                crate = crates[0]
                crate.is_default = True
                crate.save()
        else:
            crate = crates[0]

    # Get crate for given key.
    else:
        crate = models.Crate.get(crate_key)

    return crate

def _remove_crate_items(crate, crate_items=None):
    if crate_items is None:
        crate_items = reversed(crate.items)
    for key in crate_items:
        crate.items.remove(key)
        if key.kind() == 'CrateItem':
            db.delete(key)
    crate.order = range(1, len(crate.items) + 1)
    AutoRetry(crate).save()

def _sort_crate_items(sort_by, key):
    crate_item = db.get(key)
    if sort_by == 'artist':
        if crate_item.kind() == 'Artist':
            return crate_item.name
        elif crate_item.kind() == 'Album':
            return crate_item.artist_name
        elif crate_item.kind() == 'Track':
            return crate_item.artist_name
        elif crate_item.kind() == 'CrateItem':
            return crate_item.artist
    elif sort_by == 'album':
        if crate_item.kind() == 'Album':
            return crate_item.title
        elif crate_item.kind() == 'Track':
            return crate_item.album.title
        elif crate_item.kind() == 'CrateItem':
            return crate_item.album
    elif sort_by == 'track':
        if crate_item.kind() == 'Track':
            return crate_item.title
        elif crate_item.kind() == 'CrateItem':
            return crate_item.track
    elif sort_by == 'duration':
        if crate_item.kind() == 'Track':
            return crate_item.duration
    return None

def crate_page(request, crate_key=None, ctx_vars=None):
    if ctx_vars is None:
        ctx_vars = {}

    sort_by = ''
    if request.method == 'POST':
        # Save current crate info.
        if request.POST.get('save_crate'):
            crate = _get_crate(request.user, crate_key)
            crate_items_form = forms.CrateItemsForm(request.POST,
                                                    user=request.user)
            if crate_items_form.is_valid():
                crate.name = crate_items_form.cleaned_data['name']
                if request.POST.get('is_default'):
                    is_default = crate_items_form.cleaned_data['is_default']
                    if is_default:
                        default_crate = _get_crate(request.user)
                        if default_crate != crate:
                            default_crate.is_default = False
                            default_crate.save()            
                    crate.is_default = is_default
                crate.save()

        # Create a new crate.
        elif request.POST.get('new_crate'):
            crate = models.Crate(user=request.user)
            AutoRetry(db).put(crate)
            return http.HttpResponseRedirect("/djdb/crate/%s" % crate.key())

        # Remove current crate.
        elif request.POST.get('remove_crate'):
            crate = _get_crate(request.user, crate_key)
            _remove_crate_items(crate)
            db.delete(crate.key())
            return http.HttpResponseRedirect("/djdb/crate")

        # Remove current crate's items.
        elif request.POST.get('remove_all_crate_items'):
            crate = _get_crate(request.user, crate_key)
            _remove_crate_items(crate)

        # Remove selected crate items.
        elif request.POST.get('remove_selected_crate_items'):
            crate = _get_crate(request.user, crate_key)
            crate_items = []
            for name in sorted(request.POST.keys()) :
                m = re.match('crate_item_(\d+)', name)
                if m:
                    num = int(m.group(1))
                    crate_items.append(crate.items[num - 1])
            if crate_items:
                _remove_crate_items(crate, reversed(crate_items))

        elif request.POST.get('sort'):
            crate = _get_crate(request.user, crate_key)
            crate_items_form = forms.CrateItemsForm(request.POST,
                                                    user=request.user)
            if crate_items_form.is_valid():
                sort_by = crate_items_form.cleaned_data['sort_by']
                crate.items.sort(key=partial(_sort_crate_items, sort_by))

        # Comes here after adding a new crate item.
        else:
            crate = _get_crate(request.user, crate_key)                

    else:
        crate = _get_crate(request.user, crate_key)
        
    # Recreate crate items order.
    new_crate_items = []
    crate_items = []
    if crate.items:
        for pos in crate.order:
            new_crate_items.append(crate.items[pos-1])
            crate_items.append(AutoRetry(db).get(crate.items[pos-1]))
    crate.items = new_crate_items
    crate.order = range(1, len(crate.items)+1)
    crate.save()

    ctx_vars["title"] = "Your Crate"
    ctx_vars["user"] = request.user
    ctx_vars["crate_form"] = forms.CrateForm()
    ctx_vars['crate_items_form'] = forms.CrateItemsForm(
                                     {'crates': crate.key(),
                                      'name': crate.name,
                                      'is_default': crate.is_default,
                                      'sort_by': sort_by},
                                     user=request.user)
    ctx_vars["crate"] = crate
    ctx_vars["crate_items"] = crate_items

    ctx = RequestContext(request, ctx_vars)
    template = loader.get_template("djdb/crate_page.html")
    return http.HttpResponse(template.render(ctx))

def add_crate_item(request, crate_key=None):
    item = None
    if request.method == 'POST':
        form = forms.CrateForm(request.POST)
        if form.is_valid():
            artist = form.cleaned_data['artist']
            album = form.cleaned_data['album']
            track = form.cleaned_data['track']
            label = form.cleaned_data['label']
            notes = form.cleaned_data['notes']
            categories = []
            for category in models.ALBUM_CATEGORIES:
                field = 'is_%s' % category
                if field in form.cleaned_data and form.cleaned_data[field]:
                    categories.append(category)            
            if artist != "" or album != "" or track != "" or label != "":
                item = models.CrateItem(artist=artist,
                                        album=album,
                                        track=track,
                                        label=label,
                                        categories=categories,
                                        notes=notes)
                AutoRetry(db).put(item)
    else:
        item_key = request.GET.get('item_key')
        if not item_key:
            return http.HttpResponse(status=404)
        item = AutoRetry(db).get(item_key)
        if not item:
            return http.HttpResponse(status=404)

    msg = ''
    crate = _get_crate(request.user, crate_key)
    if item is not None and item.key() not in crate.items:
        crate.items.append(item.key())
        if crate.order:
            crate.order.append(max(crate.order) + 1)
        else:
            crate.order = [1]
        AutoRetry(crate).save()

#        if item.kind() == 'Artist':
#            msg = 'Artist added to your default crate,'
#        elif item.kind() == 'Album':
#            msg = 'Album added to your default crate.'
#        elif item.kind() == 'Track':
#            msg = 'Track added to your default crate.'

    response_page = request.GET.get('response_page')
    ctx_vars = { 'msg': msg }
    if response_page == 'landing':
        ctx_vars['query'] = request.GET.get('query')
        return landing_page(request, ctx_vars)
    elif response_page == 'artist':
        return artist_info_page(request, item.artist_name, ctx_vars)
    elif response_page == 'album':
        return album_info_page(request, str(item.album.album_id), ctx_vars)
    else:
        return crate_page(request, crate_key, ctx_vars)

def remove_crate_item(request, crate_key=None):
    item_key = request.GET.get('item_key')
    if not item_key:
        return http.HttpResponse(status=404)
    item = AutoRetry(db).get(item_key)
    if not item:
        return http.HttpResponse(status=404)

    msg = ''
    crate = _get_crate(request.user, crate_key)
    if item.key() in crate.items:
        remove_pos = crate.items.index(item.key())
        crate.items.remove(item.key())
        new_order = []
        for pos in crate.order:
            if pos-1 != remove_pos:
                if pos-1 > remove_pos:
                    new_order.append(pos-1)
                else:
                    new_order.append(pos)
        crate.order = new_order
        AutoRetry(crate).save()

#        if item.kind() == 'Artist':
#            msg = 'Artist removed from your default crate,'
#        elif item.kind() == 'Album':
#            msg = 'Album removed from your default crate.'
#        elif item.kind() == 'Track':
#            msg = 'Track removed from your default crate.'
        if item.kind() == 'CrateItem':
            AutoRetry(item).delete()

    response_page = request.GET.get('response_page')
    ctx_vars = { 'msg': msg }
    if response_page == 'landing':
        ctx_vars['query'] = request.GET.get('query')
        return landing_page(request, ctx_vars)
    elif response_page == 'artist':
        return artist_info_page(request, item.artist_name, ctx_vars)
    elif response_page == 'album':
        return album_info_page(request, str(item.album.album_id), ctx_vars)
    else:
        return crate_page(request, crate_key, ctx_vars)

def reorder_crate_items(request, crate_key=None):
    item = request.GET.getlist('item[]')
    crate = _get_crate(request.user, crate_key)
    crate.order = [int(u) for u in item]
    AutoRetry(crate).save()
    return http.HttpResponse(mimetype="text/plain")
    
def send_to_playlist(request, key):
    """
    Returns item info, presumably to an AJAX call.
    """
    entity = AutoRetry(db).get(key)
    artist_name = ''
    artist_key = ''
    track_title = ''
    track_key = ''
    album_title = ''
    album_key = ''
    label = ''
    notes = ''
    categories = ''
    if entity.kind() == 'Artist':
        artist_name = entity.name.strip().replace('/', '//')
        artist_key = entity.key()
    elif entity.kind() == 'Album':
        artist_name = entity.artist_name.strip().replace('/', '//')
        if entity.album_artist:
            artist_key = entity.album_artist.key()
        album_title = entity.title.strip().replace('/', '//')
        album_key = entity.key()
        categories = ','.join(entity.category_tags)
    elif entity.kind() == 'Track':
        artist_name = entity.artist_name.strip().replace('/', '//')
        if entity.track_artist:
            artist_key = entity.track_artist.key()
        elif entity.album.album_artist:
            artist_key = entity.album.album_artist.key()
        track_title = entity.title.strip().replace('/', '//')
        track_key = entity.key()
        album_title = entity.album.title.strip().replace('/', '//')
        album_key = entity.album.key()
        if entity.album.label:
            label = entity.album.label.strip().replace('/', '//')
        categories = ','.join(entity.album.category_tags)
    elif entity.kind() == 'CrateItem':
        artist_name = entity.artist.strip().replace('/', '//')
        track_title = entity.track.strip().replace('/', '//')
        album_title = entity.album.strip().replace('/', '//')
        label = entity.label.strip().replace('/', '//')
        notes = entity.notes.strip().replace('/', '//')
        categories = ','.join(entity.categories)
    else:
        raise Exception('Invalid entity sent to playlist')

    # Check if item played recently.
    error = ''
    start_dt = datetime.now() - timedelta(seconds=LAST_PLAYED_SECONDS)
    if track_key != '':
        query = PlaylistTrack.all().filter('playlist =', ChirpBroadcast()) \
                                   .filter('established >=', start_dt) \
                                   .filter('track =', track_key)
        if query.count() > 0:
            error = "Track already played within the last %d hours." % LAST_PLAYED_HOURS
    if error == '' and album_key != '':
        query = PlaylistTrack.all().filter('playlist =', ChirpBroadcast()) \
                                   .filter('established >=', start_dt) \
                                   .filter('album =', album_key)
        if query.count() > 0:
            error = "Track from album already played within the last %d hours." % LAST_PLAYED_HOURS
    if error == '' and artist_key != '':
        query = PlaylistTrack.all().filter('playlist =', ChirpBroadcast()) \
                                   .filter('established >=', start_dt) \
                                   .filter('artist =', artist_key)
        if query.count() > 0:
            error = "Track from artist already played within the last %d hours." % LAST_PLAYED_HOURS

    response = '"%s / %s / %s / %s / %s / %s / %s / %s / %s / %s"' % (artist_name, artist_key, track_title, track_key, album_title, album_key, label, notes, categories, error)

    return http.HttpResponse(response)

# Only the music director has the power to add new artists.
@require_role(roles.MUSIC_DIRECTOR)
def artists_bulk_add(request):
    tmpl = loader.get_template("djdb/artists_bulk_add.html")
    ctx_vars = {}
    # Our default is the data entry screen, where users add a list
    # of artists in a textarea.
    mode = "data_entry"
    if request.method == "POST" and request.path.endswith(".confirm"):
        bulk_input = request.POST.get("bulk_input")
        artists_to_add = [line.strip() for line in bulk_input.split("\r\n")]
        artists_to_add = sorted(line for line in artists_to_add if line)
        # TODO(trow): Should we do some sort of checking that an artist
        # doesn't already exist?
        if artists_to_add:
            ctx_vars["artists_to_add"] = artists_to_add
            mode = "confirm"
        # If the textarea was empty, we fall through.  Since we did not
        # reset the mode, the user will just get another textarea to
        # enter names into.
    elif request.method == "POST" and request.path.endswith(".do"):
        artists_to_add = request.POST.getlist("artist_name")
        search.create_artists(artists_to_add)
        mode = "do"
        ctx_vars["num_artists_added"] = len(artists_to_add)
            
    ctx_vars[mode] = True
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(tmpl.render(ctx))

def _copy_created(request):
    """
    Update documents - copy document timestamp field to created and modified
    field.
    """
    for doc in models.Document.all():
        try:
            doc.created = doc.timestamp
            doc.modified = doc.timestamp
        except:
            ""
        else:
            AutoRetry(doc).save()
    return landing_page(request)
