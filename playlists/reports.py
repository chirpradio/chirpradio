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

import csv
from datetime import datetime, timedelta
import logging

from django.http import HttpResponse
from django.template import loader, RequestContext
from django.shortcuts import render_to_response, get_object_or_404

from google.appengine.api import datastore_errors

from auth.decorators import require_role
import auth
from auth import roles
from common.utilities import (as_encoded_str, http_send_csv_file, 
                              restricted_job_worker, restricted_job_product)
from djdb.models import HEAVY_ROTATION_TAG, LIGHT_ROTATION_TAG
from playlists.forms import PlaylistTrackForm, PlaylistReportForm
from playlists.views import (query_group_by_track_key, filter_tracks_by_date_range,
                             filter_playlist_events_by_date_range)
from playlists.models import PlaylistTrack, PlaylistEvent, PlaylistBreak


log = logging.getLogger()


REPORT_FIELDS = ['from_date', 'to_date', 'album_title', 'artist_name',
                 'label', 'play_count', 'heavy_rotation', 'light_rotation']

EXPORT_REPORT_FIELDS = ['channel', 'date', 'start_time', 'end_time', 'artist_name',
                        'track_title', 'album_title', 'label']

@require_role(roles.MUSIC_DIRECTOR)
def report_playlist(request, template='playlists/reports.html'):
    vars = {}

    # report vars
    items = None
    fields = REPORT_FIELDS

    # default report
    if request.method == 'GET':
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=1)
        items = query_group_by_track_key(from_date, to_date)

        # default form
        form = PlaylistReportForm({'from_date':from_date, 'to_date':to_date})

    # check form data post
    elif request.method == 'POST':

        # generic search form
        form = PlaylistReportForm(data=request.POST)
        if form.is_valid():
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']


            # special case to download report
            if request.POST.get('download') == 'Download':
                fname = "chirp-play-count_%s_%s" % (from_date, to_date)
                return http_send_csv_file(fname, fields, query_group_by_track_key(from_date, to_date))

            # generate report from date range
            if request.POST.get('search') == 'Search':
                items = query_group_by_track_key(from_date, to_date)

    # template vars
    vars['form'] = form

    return render_to_response(template, vars,
            context_instance=RequestContext(request))


@require_role(roles.MUSIC_DIRECTOR)
def report_playlist_new(request):
    return report_playlist(request, template='playlists/new-reports.html')


@require_role(roles.MUSIC_DIRECTOR)
def report_export_playlist(request, template='playlists/export_reports.html'):
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=1)
    form = PlaylistReportForm({'from_date': from_date, 'to_date': to_date})
    vars = {'form': form}
    return render_to_response(template, vars,
            context_instance=RequestContext(request))


@restricted_job_worker('build-playlist-report', roles.MUSIC_DIRECTOR)
def playlist_report_worker(results, request_params):
    form = PlaylistReportForm(data=request_params)
    if not form.is_valid():
        # TODO(Kumar) make this visible to the user
        raise ValueError('Invalid PlaylistReportForm')
    from_date = form.cleaned_data['from_date']
    to_date = form.cleaned_data['to_date']

    if results is None:
        # when starting the job, init file lines with the header row...
        results = {
            'items': {},  # items keyed by play key
            'last_offset': 0,
            'play_counts': {},  # play keys to number of plays
            'from_date': str(from_date),
            'to_date': str(to_date),
        }

    offset = results['last_offset']
    last_offset = offset+50
    results['last_offset'] = last_offset

    query = filter_tracks_by_date_range(from_date, to_date)
    all_entries = query[ offset: last_offset ]

    if len(all_entries) == 0:
        finished = True
    else:
        finished = False

    for entry in all_entries:
        play_key = play_count_key(entry)
        if play_key in results['play_counts']:
            results['play_counts'][play_key] += 1
            continue
        else:
            results['play_counts'][play_key] = 1
        results['items'][play_key] = {
            'album_title': as_encoded_str(_get_entity_attr(entry,
                                                           'album_title')),
            'artist_name': as_encoded_str(_get_entity_attr(entry,
                                                           'artist_name')),
            'label': as_encoded_str(_get_entity_attr(entry, 'label')),
            'heavy_rotation': str(int(bool(HEAVY_ROTATION_TAG in
                                           entry.categories))),
            'light_rotation': str(int(bool(LIGHT_ROTATION_TAG in
                                           entry.categories)))
        }

    return finished, results


@restricted_job_worker('build-export-playlist-report', roles.MUSIC_DIRECTOR)
def playlist_export_report_worker(results, request_params):
    form = PlaylistReportForm(data=request_params)
    if not form.is_valid():
        # TODO(Kumar) make this visible to the user
        raise ValueError('Invalid PlaylistReportForm')
    from_date = form.cleaned_data['from_date']
    to_date = form.cleaned_data['to_date']

    if results is None:
        # when starting the job, init file lines with the header row...
        results = {
            'items': {},  # items keyed by datetime established
            'last_offset': 0,
            'from_date': str(from_date),
            'to_date': str(to_date),
        }

    offset = results['last_offset']
    last_offset = offset+50
    results['last_offset'] = last_offset

    query = filter_playlist_events_by_date_range(from_date, to_date)
    all_entries = query[ offset: last_offset ]

    if len(all_entries) == 0:
        finished = True
    else:
        finished = False

    for entry in all_entries:
        established = _get_entity_attr(entry, 'established_display')
        report_key = as_encoded_str(str(established))
      
        if type(entry) == PlaylistBreak:
            results['items'][report_key] = {
                'established': as_encoded_str(established.strftime('%Y-%m-%d %H:%M:%S')),
                'is_break': True
            }
            continue
       
        playlist = _get_entity_attr(entry, 'playlist') 
        track = _get_entity_attr(entry, 'track')
        results['items'][report_key] = {
            'channel': as_encoded_str(_get_entity_attr(playlist, 'channel')),
            'date': as_encoded_str(established.strftime("%m/%d/%y")),
            'duration_ms': as_encoded_str(_get_entity_attr(track, 
                                                           'duration_ms', 0)),
            'established': as_encoded_str(established.strftime('%Y-%m-%d %H:%M:%S')),
            'artist_name': as_encoded_str(_get_entity_attr(entry,
                                                           'artist_name')),
            'track_title': as_encoded_str(_get_entity_attr(entry,
                                                            'track_title')),
            'album_title': as_encoded_str(_get_entity_attr(entry, 
                                                           'album_title_display')),
            'label': as_encoded_str(_get_entity_attr(entry, 'label_display')),
            'is_break': False
        }

    return finished, results


def _get_entity_attr(entity, attr, *getattr_args):
    """gets the value of an attribute on an entity.

    if the value is an orphaned reference then return
    the string __bad_reference__ instead
    """
    try:
        if len(getattr_args):
            return getattr(entity, attr, *getattr_args)
        else:
            return getattr(entity, attr)
    except datastore_errors.Error, exc:
        if str(exc).startswith('ReferenceProperty failed to be resolved'):
            log.warning("Could not resolve reference property %r on %r at %s" % (
                                                            attr, entity, entity.key()))
            return '__bad_reference__'
        else:
            # something else happened
            raise


# group by key/fields
def play_count_key(item):
    """given a playlist record, generate a key to tally play counts with.

    For example: Talking Book,Stevie Wonder,Motown
    """
    key_parts = []
    for key in ['album_title', 'artist_name', 'label']:
        stub = as_encoded_str(_get_entity_attr(item, key, ''))
        stub = stub.lower()
        key_parts.append(stub)
    return ','.join(key_parts)


@restricted_job_product('build-playlist-report', roles.MUSIC_DIRECTOR)
def playlist_report_product(results):
    fname = "chirp-play-count_%s_%s" % (results['from_date'],
                                        results['to_date'])
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = "attachment; filename=%s.csv" % (fname)
    writer = csv.writer(response, REPORT_FIELDS)
    writer.writerow(REPORT_FIELDS)
    for play_key, item in results['items'].iteritems():
        item['from_date'] = results['from_date']
        item['to_date'] = results['to_date']
        item['play_count'] = results['play_counts'][play_key]
        writer.writerow([as_encoded_str(item[k], errors='replace')
                         for k in REPORT_FIELDS])
    return response


@restricted_job_product('build-export-playlist-report', roles.MUSIC_DIRECTOR)
def playlist_report_export_product(results):
    fname = "chirp-export-report_%s_%s" % (results['from_date'],
                                           results['to_date'])
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = "attachment; filename=%s.txt" % (fname)
    writer = csv.writer(response, EXPORT_REPORT_FIELDS, delimiter='\t')
    writer.writerow(EXPORT_REPORT_FIELDS)
    # sort on date and time
    sorted_keys = sorted(results['items'], reverse=True)
    # construct start and end times
    prev_established = None
    for key in sorted_keys:
        item = results['items'][key]
        established = datetime.strptime(item['established'], '%Y-%m-%d %H:%M:%S')
        if item['is_break']: 
            prev_established = established
            continue
        item['start_time'] = established.strftime('%H:%M:%S')
        # calculate end times
        if prev_established and prev_established.date() == established.date():
            item['end_time'] = (prev_established - timedelta(seconds=1)).strftime('%H:%M:%S')
        else:
            # track is last played for the day
            if item['duration_ms']:
                delta = timedelta(milliseconds=item['duration_ms'])
                item['end_time'] = (established + delta).strftime('%H:%M:%S')
            else:
                # no track duration, default to 4 minutes
                item['end_time'] = (established + timedelta(minutes=4)).strftime('%H:%M:%S')
        prev_established = established
        writer.writerow([as_encoded_str(item[k], errors='replace')
                         for k in EXPORT_REPORT_FIELDS])
    return response
