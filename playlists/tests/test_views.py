
###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the 'License');
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an 'AS IS' BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

from __future__ import with_statement

import csv
from StringIO import StringIO
import datetime
from datetime import timedelta
import unittest
# future: urlparse
import cgi

from django.test import TestCase
from django.core.urlresolvers import reverse
import fudge
from fudge.inspector import arg

from common.testutil import FormTestCaseHelper
from common import dbconfig
import auth
from auth import roles
from auth.models import User
import playlists.tasks
from playlists import views as playlists_views
from playlists.models import Playlist, PlaylistTrack, PlaylistBreak, ChirpBroadcast
from djdb.models import Artist, Album, Track

import time

__all__ = ['TestPlaylistViews', 'TestPlaylistViewsWithLibrary',
           'TestDeleteTrackFromPlaylist', 'TestLiveSitePlaylistTasks',
           'TestLive365PlaylistTasks', 'TestPlaylistReport']

# stub that does nothing to handle tests
# that don't need to make assertions about URL fetches
stub_fetch_url = fudge.Fake('_fetch_url', callable=True)

def setup_dbconfig():
    dbconfig['chirpapi.url.create'] = 'http://testapi/playlist/create'
    dbconfig['chirpapi.url.delete'] = 'http://testapi/playlist/delete'
    dbconfig['live365.service_url'] = 'http://__dummylive365service__/cgi-bin/add_song.cgi'
    dbconfig['live365.member_name'] = 'dummy_member'
    dbconfig['live365.password'] = 'dummy_password'

def clear_data():
    for pl in Playlist.all():
        for track in PlaylistTrack.all().filter('playlist =', pl):
            track.delete()
        pl.delete()

def create_stevie_wonder_album_data():
    stevie = Artist.create(name="Stevie Wonder")
    stevie.put()
    talking_book = Album(
        album_id=1, # faux
        artist=stevie,
        title="Talking Book",
        import_timestamp=datetime.datetime.now(),
        num_tracks=10)
    talking_book.put()
    tracks = {}
    for idx, title in enumerate([
            'You Are The Sunshine Of My Life',
            'Maybe Your Baby',
            'You And I (We Can Conquer The World)'
            # ...etc...
            ]):
        track = Track(
                    album=talking_book,
                    title=title,
                    sampling_rate_hz=44000,
                    bit_rate_kbps=256,
                    channels='stereo',
                    duration_ms=60*60*3, # faux
                    track_num=idx+1)
        tracks[title] = track
        track.put()

    return stevie, talking_book, tracks

class PlaylistViewsTest(FormTestCaseHelper, TestCase):

    def setUp(self):
        self.client.login(email="test@test.com", roles=[roles.DJ])
        setup_dbconfig()

    def tearDown(self):
        clear_data()
        fudge.clear_expectations()

    def get_selector(self):
        return User.all().filter('email =', 'test@test.com')[0]

class TestPlaylistReport(PlaylistViewsTest):

    def setUp(self):
        super(TestPlaylistReport, self).setUp()
        self.client.login(email="test@test.com", roles=[roles.DJ, roles.MUSIC_DIRECTOR])


    def test_report_dates(self):
        selector = self.get_selector()
        playlist = ChirpBroadcast()

        def create_track(artist, album, track, label):
            track = PlaylistTrack(
                        playlist=playlist,
                        selector=selector,
                        freeform_artist_name=artist,
                        freeform_album_title=album,
                        freeform_track_title=track,
                        freeform_label=label)
            track.put()
            return track

        # default date
        d = datetime.datetime(2010,01,10,1,1,1)

        # album 'a', will be played twice
        albums = ['a','b','c','a']
        tracks = ['a','b','c']
        for album in albums:
            for track in tracks:
                s = "%s_%s" % (album,track)
                t = create_track("artist_"+s, "album_"+album, "track_"+track, "label_"+s)
                t.established = d
                t.put()

            # change date so each album is played once in a day
            # total of len(tracks) per day
            d = d - timedelta(days=1)

        # run report check against expected counts
        total_tracks = len(albums) * len(tracks)

        # date range to get all records
        from_date = datetime.datetime(2010,01,01,0,0,0)
        to_date = datetime.datetime(2010,01,20,0,0,0)

        # test query object recs
        pl = playlists_views.filter_tracks_by_date_range(from_date, to_date)
        self.assertEquals(total_tracks, pl.count())

        # test group by query, expect a total of 9 recs since album_a was played twice
        items = playlists_views.query_group_by_track_key(from_date, to_date)
        for i in items:
            if i['album_title'] is 'album_a':
                self.assertEquals(i['play_count'], 2)
        self.assertEquals(len(items), 9)

        # check timestamp is set correctly for same date range
        from_date = to_date = datetime.datetime(2010,01,10,0,0,0)
        pl = playlists_views.filter_tracks_by_date_range(from_date, to_date)
        self.assertEquals(len(tracks), pl.count())


    def test_report_csv(self):
        selector = self.get_selector()
        playlist = ChirpBroadcast()
        stevie, talking_book, tracks = create_stevie_wonder_album_data()
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    artist=stevie,
                    album=talking_book,
                    track=tracks['You Are The Sunshine Of My Life'],
                    freeform_label='Motown')
        track.put()
        # sleep to workaround microtime issues in Windows App Engine SDK
        time.sleep(0.4)
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Def Leoppard",
                    freeform_album_title="Pyromania",
                    freeform_track_title="Photograph",
                    freeform_label="Geffen")
        track.put()
        time.sleep(0.4)
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Def Leoppard",
                    freeform_album_title="Pyromania",
                    freeform_track_title="Photograph",
                    freeform_label="Geffen")
        track.put()
        time.sleep(0.4)
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name=u'Ivan Krsti\u0107',
                    freeform_album_title=u'Ivan Krsti\u0107',
                    freeform_track_title=u'Ivan Krsti\u0107',
                    freeform_label=u'Ivan Krsti\u0107')
        track.put()

        from_date = datetime.date.today() - timedelta(days=1)
        to_date = datetime.date.today() + timedelta(days=1)

        response = self.client.post(reverse('playlists_report'), {
            'from_date': from_date,
            'to_date': to_date,
            'download': 'Download'
        })
        
        self.assertEquals(response['Content-Type'], 'text/csv; charset=utf-8')
        
        report = csv.reader(StringIO(response.content))
        self.assertEquals(
            ['from_date', 'to_date', 'album_title', 'artist_name', 'label', 'play_count'],
            report.next())
        self.assertEquals(
            [str(from_date), str(to_date),
            'Ivan Krsti\xc4\x87', 'Ivan Krsti\xc4\x87', 'Ivan Krsti\xc4\x87', '1'],
            report.next())
        self.assertEquals(
            [str(from_date), str(to_date),
            'Pyromania', 'Def Leoppard', 'Geffen', '2'],
            report.next())
        self.assertEquals(
            [str(from_date), str(to_date),
            'Talking Book', 'Stevie Wonder', 'Motown', '1'],
            report.next())
    
    def test_report_ignores_reference_errors(self):
        selector = self.get_selector()
        playlist = ChirpBroadcast()
        stevie, talking_book, tracks = create_stevie_wonder_album_data()
        track = PlaylistTrack(
                    playlist=playlist, 
                    selector=selector,
                    artist=stevie,
                    album=talking_book,
                    track=tracks['You Are The Sunshine Of My Life'],
                    freeform_label='Motown')
        track.put()
        
        # simulate an integrity error.
        # it is unlikely but happened to us after a bad data import.
        stevie.delete()
        talking_book.delete()
        
        from_date = datetime.date.today() - timedelta(days=1)
        to_date = datetime.date.today() + timedelta(days=1)
        
        response = self.client.post(reverse('playlists_report'), {
            'from_date': from_date,
            'to_date': to_date,
            'download': 'Download'
        })
        
        self.assertEquals(response['Content-Type'], 'text/csv; charset=utf-8')
        
        report = csv.reader(StringIO(response.content))
        self.assertEquals(
            ['from_date', 'to_date', 'album_title', 'artist_name', 'label', 'play_count'],
            report.next())
        self.assertEquals(
            [str(from_date), str(to_date), 
            '__bad_reference__', '__bad_reference__', 'Motown', '1'],
            report.next())

class TestPlaylistViews(PlaylistViewsTest):

    def test_view_shows_3_hours_of_tracks(self):
        selector = self.get_selector()
        playlist = ChirpBroadcast()
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Steely Dan",
                    freeform_album_title="Aja",
                    freeform_track_title="Peg")
        track.put()
        # sleep to workaround microtime issues in Windows App Engine SDK
        time.sleep(0.4)
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Def Leoppard",
                    freeform_album_title="Pyromania",
                    freeform_track_title="Photograph")
        track.put()
        time.sleep(0.4)
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Freestyle Fellowship",
                    freeform_album_title="To Whom It May Concern",
                    freeform_track_title="Five O'Clock Follies")
        # older than 3 hours:
        track.established = datetime.datetime.now() - datetime.timedelta(hours=3, minutes=2)
        track.put()

        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].track_title, "Photograph")
        self.assertEquals(tracks[1].track_title, "Peg")
        self.assertEquals(len(tracks), 2, "tracks older than 3 hours were not hidden")

    def test_incomplete_track(self):
        selector = self.get_selector()
        playlist = ChirpBroadcast()
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Squarepusher",
                    freeform_track_title="Port Rhombus")
        track.put()

        with fudge.patched_context(playlists.tasks, "_fetch_url", stub_fetch_url):
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist': 'Julio Iglesias',
                'album': 'Mi Amore'
            })
        # self.assertNoFormErrors(resp)
        context = resp.context[0]
        self.assertEqual(context['form'].errors.as_text(),
            "* song\n  * Please enter the song title.\n* label\n  * Please enter the label.")
        assert 'Please enter the label.' in resp.content
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")

    def test_add_track_with_minimal_fields(self):

        def inspect_request(r):
            # NOTE: due to URL fetching, you can only raise
            # AssertionError here
            self.assertEqual(r.get_full_url(), 'http://testapi/playlist/create')
            qs = dict(cgi.parse_qsl(r.data))
            self.assertEqual(qs['dj_name'], "None None")
            self.assertEqual(qs['track_artist'], 'Squarepusher')
            self.assertEqual(qs['track_name'], 'Port Rhombus')
            self.assertEqual(qs['track_album'], 'Port Rhombus EP')
            self.assertEqual(qs['track_label'], 'Warp Records')

            # left empty:
            assert 'track_notes' not in qs
            assert 'time_played' in qs
            assert 'track_id' in qs
            return True

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .with_args(arg.passes_test(inspect_request)))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist': "Squarepusher",
                'song': "Port Rhombus",
                "album": "Port Rhombus EP",
                "label": "Warp Records"
            })
        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")
        self.assertEquals(tracks[0].album_title, "Port Rhombus EP")
        self.assertEquals(tracks[0].label, "Warp Records")

        # when this user has created the entry she gets a link to delete it
        assert '[delete]' in resp.content
        fudge.verify()

    def test_remote_api_errors_are_logged(self):

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .raises(IOError("something bad happened on remote API")))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist': "Squarepusher",
                'song': "Port Rhombus",
            })

    def test_add_track_with_all_fields(self):

        def inspect_request(r):
            # NOTE: due to URL fetching, you can only raise
            # AssertionError here
            self.assertEqual(r.get_full_url(), 'http://testapi/playlist/create')
            qs = dict(cgi.parse_qsl(r.data))
            self.assertEqual(qs['dj_name'], "None None")
            self.assertEqual(qs['track_artist'], 'Squarepusher')
            self.assertEqual(qs['track_name'], 'Port Rhombus')
            self.assertEqual(qs['track_album'], 'Port Rhombus EP')
            self.assertEqual(qs['track_label'], 'Warp Records')
            self.assertEqual(qs['track_notes'], "Dark melody. Really nice break down into half time.")
            assert 'time_played' in qs
            assert 'track_id' in qs
            return True

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .with_args(arg.passes_test(inspect_request)))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        fake_taskqueue = (fudge.Fake('taskqueue')
                                .expects('add')
                                .with_args(
                                    url=reverse('playlists.send_track_to_live365'),
                                    params={'id': arg.any_value()}
                                ))
        patches = [
            fudge.patch_object(playlists.tasks.urllib2, "urlopen", fake_urlopen),
            fudge.patch_object(playlists.tasks, "taskqueue", fake_taskqueue)
        ]
        try:
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist': "Squarepusher",
                'song': "Port Rhombus",
                "album": "Port Rhombus EP",
                "label": "Warp Records",
                "song_notes": "Dark melody. Really nice break down into half time."
            })
        finally:
            for p in patches:
                p.restore()

        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Squarepusher")
        self.assertEquals(tracks[0].track_title, "Port Rhombus")
        self.assertEquals(tracks[0].album_title, "Port Rhombus EP")
        self.assertEquals(tracks[0].label, "Warp Records")
        self.assertEquals(tracks[0].notes,
                "Dark melody. Really nice break down into half time.")
        fudge.verify()

    def test_add_tracks_to_existing_stream(self):
        # add several tracks:
        with fudge.patched_context(playlists.tasks, "_fetch_url", stub_fetch_url):
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist': "Steely Dan",
                'song': "Peg",
                'album': "Aja",
                'label': "ABC",
            })
            self.assertNoFormErrors(resp)
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist': "Hall & Oates",
                'song': "M.E.T.H.O.D. of Love",
                'album': "Big Bam Boom",
                'label': 'RCA'
            })
            self.assertNoFormErrors(resp)

        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Hall & Oates")
        self.assertEquals(tracks[1].artist_name, "Steely Dan")

    def test_unicode_track_entry(self):

        def inspect_request(r):
            # NOTE: due to URL fetching, you can only raise
            # AssertionError here
            self.assertEqual(r.get_full_url(), 'http://testapi/playlist/create')
            qs = dict(cgi.parse_qsl(r.data))
            self.assertEqual(qs['dj_name'], "None None")
            self.assertEqual(qs['track_album'], 'Ivan Krsti\xc4\x87')
            self.assertEqual(qs['track_artist'], 'Ivan Krsti\xc4\x87')
            self.assertEqual(qs['track_label'], 'Ivan Krsti\xc4\x87')
            self.assertEqual(qs['track_name'], 'Ivan Krsti\xc4\x87')
            assert 'time_played' in qs
            assert 'track_id' in qs
            return True

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .with_args(arg.passes_test(inspect_request)))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist': u'Ivan Krsti\u0107',
                'song': u'Ivan Krsti\u0107',
                "album": u'Ivan Krsti\u0107',
                "label": u'Ivan Krsti\u0107',
                "song_notes": u'Ivan Krsti\u0107'
            })

        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].track_title, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].album_title, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].label, u'Ivan Krsti\u0107')
        self.assertEquals(tracks[0].notes, u'Ivan Krsti\u0107')

    def test_add_break(self):
        playlist = ChirpBroadcast()
        selector = self.get_selector()
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Steely Dan",
                    freeform_album_title="Aja",
                    freeform_track_title="Peg")
        track.put()
        time.sleep(0.4)
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Def Leoppard",
                    freeform_album_title="Pyromania",
                    freeform_track_title="Photograph")
        track.put()

        # add the break:
        resp = self.client.post(reverse('playlists_add_event'), {
            'submit': "Add Break",
            'artist': "artist",
            'song': "song",
            'album': "album",
            'song_notes': "song notes"
        })
        # self.assertNoFormErrors(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['form']['artist'].data, 'artist')
        self.assertEqual(resp.context['form']['song'].data, 'song')
        self.assertEqual(resp.context['form']['album'].data, 'album')
        self.assertEqual(resp.context['form']['song_notes'].data, 'song notes')

        # make sure form errors are not in response:
        assert 'Please enter the label' not in resp.content

        # add one track after the break:
        track = PlaylistTrack(
                    playlist=playlist,
                    selector=selector,
                    freeform_artist_name="Kid Sister",
                    freeform_album_title="Ultraviolet",
                    freeform_track_title="Right Hand Hi")
        track.put()

        resp = self.client.get(reverse('playlists_landing_page'))

        context = resp.context[0]
        events = [t for t in context['playlist_events']]

        self.assertEqual(events[0].artist_name, "Kid Sister")
        self.assertEqual(events[0].is_break, False)
        self.assertEqual(events[0].is_new, True)

        self.assertEqual(events[1].is_break, True)
        self.assertEqual(events[1].is_new, False)

        self.assertEqual(events[2].artist_name, "Def Leoppard")
        self.assertEqual(events[2].is_break, False)
        self.assertEqual(events[2].is_new, False)

        self.assertEqual(events[3].artist_name, "Steely Dan")
        self.assertEqual(events[3].is_break, False)
        self.assertEqual(events[3].is_new, False)

        # print resp.content
        assert '<p class="break">Break</p>' in resp.content
        assert '<p><span class="artist">Def Leoppard</span>' in resp.content
        assert '<p><span class="artist">Steely Dan</span>' in resp.content

class TestPlaylistViewsWithLibrary(PlaylistViewsTest):

    def setUp(self):
        super(TestPlaylistViewsWithLibrary, self).setUp()
        self.stevie, self.talking_book, self.tracks = create_stevie_wonder_album_data()

    def tearDown(self):
        for model in (
                PlaylistTrack, Playlist, User,
                Album, Artist, Track ):
            for obj in model.all():
                obj.delete()

    def test_add_track_linked_to_library(self):
        stevie = Artist.all().filter("name =", "Stevie Wonder")[0]
        talking_book = Album.all().filter("title =", "Talking Book")[0]
        sunshine = Track.all().filter("title =", "You Are The Sunshine Of My Life")[0]

        with fudge.patched_context(playlists.tasks, "_fetch_url", stub_fetch_url):
            resp = self.client.post(reverse('playlists_add_event'), {
                'artist_key': stevie.key(),
                'artist': stevie.name,
                'song': "You Are The Sunshine Of My Life",
                'song_key': sunshine.key(),
                'album_key': talking_book.key(),
                'album': talking_book.title,
                'label': "Tamla",
                'label_key': 'Blah'
            })

        self.assertNoFormErrors(resp)
        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Stevie Wonder")
        self.assertEquals(tracks[0].artist.key(), stevie.key())
        self.assertEquals(tracks[0].album_title, "Talking Book")
        self.assertEquals(tracks[0].album.key(), talking_book.key())
        self.assertEquals(tracks[0].track_title, "You Are The Sunshine Of My Life")
        self.assertEquals(tracks[0].track.key(), sunshine.key())

class TestDeleteTrackFromPlaylist(PlaylistViewsTest):

    def setUp(self):
        super(TestDeleteTrackFromPlaylist, self).setUp()
        self.playlist = ChirpBroadcast()
        selector = self.get_selector()
        self.track = PlaylistTrack(
                    playlist=self.playlist,
                    selector=selector,
                    freeform_artist_name="Steely Dan",
                    freeform_album_title="Aja",
                    freeform_track_title="Peg")
        self.track.put()

    def test_delete_known_track(self):
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Steely Dan")

        def inspect_request(r):
            self.assertEqual(r.get_full_url(),
                'http://testapi/playlist/delete/%s' % self.track.key())
            self.assertEqual(r.http_method, 'DELETE')
            return True

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .with_args(arg.passes_test(inspect_request)))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.get(reverse('playlists_delete_event',
                                            args=[self.track.key()]))

        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks, [])

    def test_delete_unknown_track(self):
        resp = self.client.get(reverse('playlists_landing_page'))
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Steely Dan")

        resp = self.client.get(reverse('playlists_delete_event',
                                        args=['<bogus-key>']))

        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))

        # should be no change:
        context = resp.context[0]
        tracks = [t for t in context['playlist_events']]
        self.assertEquals(tracks[0].artist_name, "Steely Dan")

    def test_cannot_delete_someone_elses_track(self):
        other_user = User(email="other@elsewhere.com")
        other_user.roles.append(auth.roles.DJ)
        other_user.put()
        time.sleep(0.4)

        other_track = PlaylistTrack(
                    playlist=self.playlist,
                    selector=other_user,
                    freeform_artist_name="Peaches",
                    freeform_track_title="Rock Show",)
        other_track.put()

        with fudge.patched_context(playlists.tasks, "_fetch_url", stub_fetch_url):
            resp = self.client.get(reverse('playlists_delete_event',
                                            args=[other_track.key()]))

        self.assertRedirects(resp, reverse('playlists_landing_page'))
        # simulate the redirect:
        resp = self.client.get(reverse('playlists_landing_page'))

        # should be no change:
        context = resp.context[0]
        tracks = [t.artist_name for t in context['playlist_events']]
        self.assertEquals(tracks, ["Peaches", "Steely Dan"])

    def test_delete_link_appears_for_current_user(self):
        resp = self.client.get(reverse('playlists_landing_page'))
        assert '[delete]' in resp.content

        for track in PlaylistTrack.all():
            track.delete()

        other_user = User(email="other@elsewhere.com")
        other_user.roles.append(auth.roles.DJ)
        other_user.put()
        other_track = PlaylistTrack(
                    playlist=self.playlist,
                    selector=other_user,
                    freeform_artist_name="Peaches",
                    freeform_track_title="Rock Show")
        other_track.put()

        resp = self.client.get(reverse('playlists_landing_page'))
        assert '[delete]' not in resp.content

class TaskTest(object):

    def get_selector(self):
        user = User(email='test@test.com')
        user.roles = [roles.DJ]
        user.save()
        return user

    def setUp(self):
        setup_dbconfig()
        self.playlist = ChirpBroadcast()
        selector = self.get_selector()
        self.track = PlaylistTrack(
                    playlist=self.playlist,
                    selector=selector,
                    freeform_artist_name=u"Ivan Krsti\u0107",
                    freeform_album_title=u"Ivan Krsti\u0107 album",
                    freeform_track_title=u"Ivan Krsti\u0107 song")
        self.track.put()

    def tearDown(self):
        clear_data()
        fudge.clear_expectations()

class TestLiveSitePlaylistTasks(TaskTest, TestCase):

    def test_create(self):

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists.send_track_to_live_site'), {
                'id': self.track.key()
            })

        fudge.verify()
    
    def test_create_non_existant_track(self):
        key = self.track.key()
        self.track.delete() # make it non-existant
        resp = self.client.post(reverse('playlists.send_track_to_live_site'), {
            'id': key
        })
        self.assertEqual(resp.status_code, 200)
    
    def test_create_failure(self):

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                            .raises(IOError))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists.send_track_to_live_site'), {
                'id': self.track.key()
            })

        self.assertEqual(resp.status_code, 500)
        # from django.utils import simplejson

        fudge.verify()

    def test_delete(self):

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            self.client.post(reverse('playlists.delete_track_from_live_site'), {
                'id': self.track.key()
            })

        fudge.verify()

    def test_delete_failure(self):

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                            .raises(IOError))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists.delete_track_from_live_site'), {
                'id': self.track.key()
            })

        self.assertEqual(resp.status_code, 500)
        fudge.verify()

class TestLive365PlaylistTasks(TaskTest, TestCase):

    def test_create_not_latin_chars(self):

        def inspect_request(r):
            # NOTE: due to URL fetching, you can only raise
            # AssertionError here
            self.assertEqual(r.get_full_url(), 'http://__dummylive365service__/cgi-bin/add_song.cgi')
            qs = dict(cgi.parse_qsl(r.data))
            self.assertEqual(qs['member_name'], "dummy_member")
            self.assertEqual(qs['password'], "dummy_password")
            self.assertEqual(qs['seconds'], '30')
            # c should be replaced because latin-1 can't encode that and Live365 likes latin-1
            self.assertEqual(qs['title'], 'Ivan Krsti song')
            self.assertEqual(qs['album'], 'Ivan Krsti album')
            self.assertEqual(qs['artist'], 'Ivan Krsti')
            return True

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .with_args(arg.passes_test(inspect_request)))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists.send_track_to_live365'), {
                'id': self.track.key()
            })

        fudge.verify()

    def test_create_latin_chars(self):

        self.playlist = ChirpBroadcast()
        selector = self.get_selector()
        self.track = PlaylistTrack(
                    playlist=self.playlist,
                    selector=selector,
                    freeform_artist_name=u'Bj\xf6rk',
                    freeform_album_title=u'Bj\xf6rk album',
                    freeform_track_title=u'Bj\xf6rk song')
        self.track.put()

        def inspect_request(r):
            # NOTE: due to URL fetching, you can only raise
            # AssertionError here
            self.assertEqual(r.get_full_url(), 'http://__dummylive365service__/cgi-bin/add_song.cgi')
            qs = dict(cgi.parse_qsl(r.data))
            self.assertEqual(qs['member_name'], "dummy_member")
            self.assertEqual(qs['password'], "dummy_password")
            self.assertEqual(qs['seconds'], '30')
            # c should be replaced because latin-1 can't encode that and Live365 likes latin-1
            self.assertEqual(qs['title'], 'Bj\xf6rk song')
            self.assertEqual(qs['album'], 'Bj\xf6rk album')
            self.assertEqual(qs['artist'], 'Bj\xf6rk')
            return True

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .with_args(arg.passes_test(inspect_request)))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists.send_track_to_live365'), {
                'id': self.track.key()
            })

        fudge.verify()

    def test_create_ascii_chars(self):

        self.playlist = ChirpBroadcast()
        selector = self.get_selector()
        self.track = PlaylistTrack(
                    playlist=self.playlist,
                    selector=selector,
                    freeform_artist_name=u'artist',
                    freeform_album_title=u'album',
                    freeform_track_title=u'song')
        self.track.put()

        def inspect_request(r):
            # NOTE: due to URL fetching, you can only raise
            # AssertionError here
            self.assertEqual(r.get_full_url(), 'http://__dummylive365service__/cgi-bin/add_song.cgi')
            qs = dict(cgi.parse_qsl(r.data))
            self.assertEqual(qs['member_name'], "dummy_member")
            self.assertEqual(qs['password'], "dummy_password")
            self.assertEqual(qs['seconds'], '30')
            # c should be replaced because latin-1 can't encode that and Live365 likes latin-1
            self.assertEqual(qs['title'], 'song')
            self.assertEqual(qs['album'], 'album')
            self.assertEqual(qs['artist'], 'artist')
            return True

        fake_urlopen = (fudge.Fake('urlopen', expect_call=True)
                                .with_args(arg.passes_test(inspect_request)))

        fake_response = (fake_urlopen
                                .returns_fake()
                                .has_attr(code='200')
                                .provides('read')
                                .returns("<service response>"))

        with fudge.patched_context(playlists.tasks.urllib2, "urlopen", fake_urlopen):
            resp = self.client.post(reverse('playlists.send_track_to_live365'), {
                'id': self.track.key()
            })

        fudge.verify()
    
    def test_create_non_existant_track(self):
        key = self.track.key()
        self.track.delete() # make it non-existant
        resp = self.client.post(reverse('playlists.send_track_to_live365'), {
            'id': key
        })
        self.assertEqual(resp.status_code, 200)


