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

import logging

from google.appengine.ext import db
from django import forms
from django import http
from django.template import loader, Context, RequestContext

from auth.decorators import require_role
from auth import roles
from common import sanitize_html
from common.autoretry import AutoRetry
from djdb import models
from djdb import search
from djdb import review
from djdb import comment

from djdb.models import Album
import re
import tag_util

log = logging.getLogger(__name__)

def landing_page(request, ctx_vars=None):
    template = loader.get_template('djdb/landing_page.html')
    if ctx_vars is None : ctx_vars = {}
    ctx_vars['title'] = 'DJ Database'

    # Grab recent reviews.
    ctx_vars["recent_reviews"] = review.fetch_recent()

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
        if reviewed is None: reviewed = False
        else: reviewed = True
        matches = search.simple_music_search(query_str, reviewed=reviewed, user_key=user_key)
        if matches is None:
            ctx_vars["invalid_query"] = True
        else:
            ctx_vars["query_results"] = matches

    # Add categories.
    ctx_vars["categories"] = models.ALBUM_CATEGORIES
    
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def artist_info_page(request, artist_name, ctx_vars=None):
    artist = models.Artist.fetch_by_name(artist_name)
    if artist is None:
        return http.HttpResponse(status=404)
    template = loader.get_template("djdb/artist_info_page.html")
    if ctx_vars is None : ctx_vars = {}
    ctx_vars["title"] = artist.pretty_name
    ctx_vars["artist"] = artist
    ctx_vars["categories"] = models.ALBUM_CATEGORIES
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def artist_search_for_autocomplete(request):
    matching_entities = _get_matches_for_partial_entity_search(
                                            request.GET.get('q', ''),
                                            'Artist')        
    response = http.HttpResponse(mimetype="text/plain")
    for ent in matching_entities:
        response.write("%s|%s\n" % (ent.pretty_name, ent.key()))
    return response

def album_search_for_autocomplete(request):
    matching_entities = _get_matches_for_partial_entity_search(
                                            request.GET.get('q', ''),
                                            'Album')        
    response = http.HttpResponse(mimetype="text/plain")
    for ent in matching_entities:
        response.write("%s|%s\n" % (ent.title, ent.key()))
    return response

@require_role(roles.MUSIC_DIRECTOR)
def album_change_categories(request) :
    for name in request.POST.keys() :
        if re.match('checkbox_', name) :
            type, num = name.split('_')
            category = request.POST.get('category_%s' % num)
            album_key = request.POST.get('album_key_%s' % num)
            album = AutoRetry(Album).get(album_key)
            album.category = category
            AutoRetry(album).save()

    if request.POST.get('response_page') == 'artist' :
        return artist_info_page(request, request.POST.get('artist_name'))
    else :
        return landing_page(request)

def album_update_tracks(request, album_id_str):
    album = _get_album_or_404(album_id_str)
    mark_as = request.POST.get('mark_as')
    for name in request.POST.keys() :
        if re.match('checkbox_', name) :
            type, num = name.split('_')
            track = album.sorted_tracks[int(num) - 1]
            if mark_as == 'explicit' :
                if models.EXPLICIT_TAG in models.TagEdit.fetch_and_merge(track) :
                    tag_util.remove_tag_and_save(request.user, track, models.EXPLICIT_TAG)
                else :
                    tag_util.add_tag_and_save(request.user, track, models.EXPLICIT_TAG)
            elif mark_as == 'recommended' :
                if models.RECOMMENDED_TAG in models.TagEdit.fetch_and_merge(track) :
                    tag_util.remove_tag_and_save(request.user, track, models.RECOMMENDED_TAG)
                else :
                    tag_util.add_tag_and_save(request.user, track, models.RECOMMENDED_TAG)
            
    template = loader.get_template("djdb/album_info_page.html")
    ctx_vars = { "title": u"%s / %s" % (album.title, album.artist_name),
                 "album": album,
                 "user": request.user }
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
                    
        response.write("%s|%s\n" % (track.title, track.key()))
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
    for album in AutoRetry(q).fetch(1):
        pass
    if album is None:
        return http.HttpResponse(status=404)
    return album

def album_info_page(request, album_id_str, ctx_vars=None):
    album = _get_album_or_404(album_id_str)
    template = loader.get_template("djdb/album_info_page.html")
    if ctx_vars is None : ctx_vars = {}
    ctx_vars["title"] = u"%s / %s" % (album.title, album.artist_name)
    ctx_vars["album"] = album
    ctx_vars["user"] = request.user
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def album_new_review(request, album_id_str):
    album = _get_album_or_404(album_id_str)
    template = loader.get_template("djdb/album_new_review.html")
    ctx_vars = { "title": u"New Review", "album": album }
    form = None
    if request.method == "GET":
        form = review.Form()
    else:
        form = review.Form(request.POST)
        if form.is_valid():
            if "preview" in request.POST:
                ctx_vars["valid_html_tags"] = (
                    sanitize_html.valid_tags_description())
                ctx_vars["preview"] = sanitize_html.sanitize_html(
                    form.cleaned_data["text"])
            elif "save" in request.POST:
                doc = review.new(album, request.user)
                doc.unsafe_text = form.cleaned_data["text"]
                # Increment the number of reviews.
                album.num_reviews += 1
                # Now save both the modified album and the document.
                # They are both in the same entity group, so this write
                # is atomic.
                AutoRetry(db).put([album, doc])
                # Redirect back to the album info page.
                return http.HttpResponseRedirect("info")
    ctx_vars["form"] = form
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def album_edit_review(request, album_id_str, review_key):
    album = _get_album_or_404(album_id_str)
    doc = review.get_or_404(review_key)
    template = loader.get_template("djdb/album_edit_review.html")
    ctx_vars = { "title": u"Edit Review",
                 "album": album,
                 "review": doc }

    form = None
    if request.method == "GET":
        form = review.Form({'text': doc.text})
    else:
        form = review.Form(request.POST)
        if form.is_valid():
            if "preview" in request.POST:
                ctx_vars["valid_html_tags"] = (
                    sanitize_html.valid_tags_description())
                ctx_vars["preview"] = sanitize_html.sanitize_html(
                    form.cleaned_data["text"])
            elif "save" in request.POST:
                doc.unsafe_text = form.cleaned_data["text"]
                AutoRetry(doc).save()
                # Redirect back to the album info page.
                return http.HttpResponseRedirect(album.url)
    ctx_vars["form"] = form
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def album_new_comment(request, album_id_str):
    album = _get_album_or_404(album_id_str)
    template = loader.get_template("djdb/album_new_comment.html")
    ctx_vars = { "title": u"New Comment", "album": album }
    form = None
    if request.method == "GET":
        form = comment.Form()
    else:
        form = comment.Form(request.POST)
        if form.is_valid():
            if "preview" in request.POST:
                ctx_vars["valid_html_tags"] = (
                    sanitize_html.valid_tags_description())
                ctx_vars["preview"] = sanitize_html.sanitize_html(
                    form.cleaned_data["text"])
            elif "save" in request.POST:
                doc = comment.new(album, request.user)
                doc.unsafe_text = form.cleaned_data["text"]
                # Increment the number of commentss.
                album.num_comments += 1
                # Now save both the modified album and the document.
                # They are both in the same entity group, so this write
                # is atomic.
                AutoRetry(db).put([album, doc])
                # Redirect back to the album info page.
                return http.HttpResponseRedirect("info")
    ctx_vars["form"] = form
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def album_edit_comment(request, album_id_str, comment_key):
    album = _get_album_or_404(album_id_str)
    doc = comment.get_or_404(comment_key)
    template = loader.get_template("djdb/album_edit_comment.html")
    ctx_vars = { "title": u"Edit Comment",
                 "album": album,
                 "comment": doc }

    form = None
    if request.method == "GET":
        form = comment.Form({'text': doc.text})
    else:
        form = comment.Form(request.POST)
        if form.is_valid():
            if "preview" in request.POST:
                ctx_vars["valid_html_tags"] = (
                    sanitize_html.valid_tags_description())
                ctx_vars["preview"] = sanitize_html.sanitize_html(
                    form.cleaned_data["text"])
            elif "save" in request.POST:
                doc.unsafe_text = form.cleaned_data["text"]
                AutoRetry(doc).save()
                # Redirect back to the album info page.
                return http.HttpResponseRedirect(album.url)
    ctx_vars["form"] = form
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def image(request):
    img = models.DjDbImage.get_by_url(request.path)
    if img is None:
        return http.HttpResponse(status=404)
    return http.HttpResponse(content=img.image_data,
                             mimetype=img.image_mimetype)

def _get_crate(user):
    crate = AutoRetry(models.Crate.all().filter("user =", user)).fetch(1)
    if len(crate) == 0:
        crate = models.Crate(user=user)
        AutoRetry(db).put(crate)
    else:
        crate = crate[0]
    return crate

def crate_page(request, ctx_vars=None):
    crate_items = AutoRetry(models.CrateItem.all().filter("user =", request.user)).fetch(999)
    template = loader.get_template("djdb/crate_page.html")
    crate = _get_crate(request.user)
    new_crate_items = []
    crate_items = []
    if crate.items :
        for pos in crate.order:
            new_crate_items.append(crate.items[pos-1])
            crate_items.append(AutoRetry(db).get(crate.items[pos-1]))
    crate.items = new_crate_items
    crate.order = range(1, len(crate.items)+1)
    crate.save()
    
    if ctx_vars is None : ctx_vars = {}
    ctx_vars["crate_items"] = crate_items
    ctx_vars["user"] = request.user
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def add_crate_item(request):
    if request.method == 'POST':
        artist = request.POST.get('artist')
        album = request.POST.get('album')
        track = request.POST.get('track')
        label = request.POST.get('label')
        notes = request.POST.get('notes')
        item = models.CrateItem(artist=artist,
                                album=album,
                                track=track,
                                label=label,
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
    crate = _get_crate(request.user)
    if item.key() not in crate.items:
        crate.items.append(item.key())
        if crate.order:
            crate.order.append(max(crate.order) + 1)
        else:
            crate.order = [1]
        AutoRetry(crate).save()

        if item.kind() == 'Artist':
            msg = 'Artist added to crate,'
        elif item.kind() == 'Album':
            msg = 'Album added to crate.'
        elif item.kind() == 'Track':
            msg = 'Track added to crate.'

    response_page = request.GET.get('response_page')
    ctx_vars = { 'msg': msg }
    if response_page == 'landing':
        ctx_vars = { 'query': request.GET.get('query') }
        return landing_page(request, ctx_vars)
    elif response_page == 'artist':
        return artist_info_page(request, item.album_artist.name, ctx_vars)
    elif response_page == 'album':
        return album_info_page(request, str(item.album.album_id), ctx_vars)
    else:
        return crate_page(request, ctx_vars)

def remove_crate_item(request):
    item_key = request.GET.get('item_key')
    if not item_key:
        return http.HttpResponse(status=404)
    item = AutoRetry(db).get(item_key)
    if not item:
        return http.HttpResponse(status=404)

    msg = ''
    crate = _get_crate(request.user)
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

        if item.kind() == 'Artist':
            msg = 'Artist removed from crate,'
        elif item.kind() == 'Album':
            msg = 'Album removed from crate.'
        elif item.kind() == 'Track':
            msg = 'Track removed from crate.'

    response_page = request.GET.get('response_page')
    ctx_vars = { 'msg': msg }
    if response_page == 'landing':
        ctx_vars['query'] = request.GET.get('query')
        return landing_page(request, ctx_vars)
    elif response_page == 'artist':
        return artist_info_page(request, item.album_artist.name, ctx_vars)
    elif response_page == 'album':
        return album_info_page(request, str(item.album.album_id), ctx_vars)
    else:
        return crate_page(request, ctx_vars)

def reorder(request):
    item = request.GET.getlist('item[]')
    crate = _get_crate(request.user)
    crate.order = [int(u) for u in item]
    AutoRetry(crate).save()
    return http.HttpResponse(mimetype="text/plain")

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
