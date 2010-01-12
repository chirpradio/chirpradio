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

from google.appengine.ext import db
from django import forms
from django import http
from django.template import loader, Context, RequestContext
from django.shortcuts import render_to_response
from auth.decorators import require_role
from auth import roles
from common import sanitize_html
from djdb import models
from djdb import search
from djdb import review
import logging
from djdb.models import Album
import re

log = logging.getLogger(__name__)


def landing_page(request):
    template = loader.get_template('djdb/landing_page.html')
    ctx_vars = { 'title': 'DJ Database' }

    # Grab recent reviews.
    ctx_vars["recent_reviews"] = review.fetch_recent()

    if request.method == "POST":
        query_str = request.POST.get("query")
        if query_str:
            ctx_vars["query_str"] = query_str
            reviewed = True
            if request.POST.get("reviewed") is None :
                reviewed = False
            matches = search.simple_music_search(query_str, reviewed=reviewed)
            if matches is None:
                ctx_vars["invalid_query"] = True
            else:
                ctx_vars["query_results"] = matches

    # Add categories.
    ctx_vars["categories"] = ['core', 'local_current', 'local_classic', 'heavy', 'light']
    
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))


def artist_info_page(request, artist_name):
    artist = models.Artist.fetch_by_name(artist_name)
    if artist is None:
        return http.HttpResponse(status=404)
    template = loader.get_template("djdb/artist_info_page.html")
    ctx_vars = { "title": artist.pretty_name,
                 "artist": artist,
                 }
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

def album_change_categories(request) :
    for name in request.POST.keys() :
        if re.match('checkbox_', name) :
            type, num = name.split('_')
            category = request.POST.get('category_%s' % num)
            album_key = request.POST.get('album_key_%s' % num)
            album = Album.get(album_key)
            album.category = category
            album.save()

    return landing_page(request)

def _add_track_tags(track, user, tags) :
    tag_edit = models.TagEdit(subject=track,
                              author=user,
                              added=tags)
    tag_edit.put()

def _remove_track_tags(track, user, tags) :
    tag_edit = models.TagEdit(subject=track,
                              author=user,
                              removed=tags);
    tag_edit.put()

def album_update_tracks(request, album_id_str):
    album = _get_album_or_404(album_id_str)
    mark_as = request.POST.get('mark_as')
    for name in request.POST.keys() :
        if re.match('checkbox_', name) :
            type, num = name.split('_')
            track = album.sorted_tracks[int(num) - 1]
            if mark_as == 'explicit' :
                if models.EXPLICIT_TAG in models.TagEdit.fetch_and_merge(track) :
                    _remove_track_tags(track, request.user, [models.EXPLICIT_TAG])
                else :
                    _add_track_tags(track, request.user, [models.EXPLICIT_TAG])
            elif mark_as == 'recommended' :
                if models.RECOMMENDED_TAG in models.TagEdit.fetch_and_merge(track) :
                    _remove_track_tags(track, request.user, [models.RECOMMENDED_TAG])
                else :
                    _add_track_tags(track, request.user, [models.RECOMMENDED_TAG])
            # Update current_tags.
            models.TagEdit.fetch_and_merge(track)
            
    template = loader.get_template("djdb/album_info_page.html")
    ctx_vars = { "title": u"%s / %s" % (album.title, album.artist_name),
                 "album": album,
                 "user": request.user }
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
    for album in q.fetch(1):
        pass
    if album is None:
        return http.HttpResponse(status=404)
    return album

def _get_review_or_404(review_key):
    doc = db.get(review_key)
    if doc is None :
        return http.HttpResponse(status=404)
    return doc

def album_info_page(request, album_id_str):
    album = _get_album_or_404(album_id_str)
    template = loader.get_template("djdb/album_info_page.html")
    ctx_vars = { "title": u"%s / %s" % (album.title, album.artist_name),
                 "album": album,
                 "user": request.user }
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
                db.put([album, doc])
                # Redirect back to the album info page.
                return http.HttpResponseRedirect("info")
    ctx_vars["form"] = form
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(template.render(ctx))

def album_edit_review(request, album_id_str, review_key):
    album = _get_album_or_404(album_id_str)
    doc = _get_review_or_404(review_key)
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
                doc.save()
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
