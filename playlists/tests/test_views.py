
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

import cgi
import datetime
from datetime import timedelta
import os
from StringIO import StringIO
import unittest
# future: urlparse

from django.test import TestCase, Client
from django.core.urlresolvers import reverse
import fudge
from fudge.inspector import arg
from nose.tools import eq_

from common.testutil import FormTestCaseHelper
from common import dbconfig
import auth
from auth import roles
from auth.models import User
import playlists.tasks
from playlists import views as playlists_views
from playlists.models import (Playlist, PlaylistTrack, PlaylistBreak,
                              ChirpBroadcast, PlayCount)
from djdb.models import Artist, Album, Track

import time

__all__ = ['TestPlaylistViews', 'TestPlaylistViewsWithLibrary',
           'TestDeleteTrackFromPlaylist', 'TestLiveSitePlaylistTasks',
           'TestLive365PlaylistTasks']

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
    for ob in PlayCount.all():
        ob.delete()

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
            'You And I (We Can Conquer The World)',
            'Tuesday Heartbreak',
            "You've Got It Bad Girl",
            'Superstition',
            'Big Brother',
            'Blame It On The Sun',
            "Lookin' For Another Pure Love",
            'I Believe (When I Fall In Love It Will Be Forever)'
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
        assert self.client.login(email="test@test.com", roles=[roles.DJ])
        setup_dbconfig()

    def tearDown(self):
        clear_data()
        fudge.clear_expectations()

    def get_selector(self):
        return User.all().filter('email =', 'test@test.com')[0]

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

    @fudge.patch('playlists.tasks.taskqueue')
    def test_add_track_with_all_fields(self, fake_tq):
        (fake_tq.expects('add')
                .with_args(
                    url=reverse('playlists.send_track_to_live_site'),
                    params={'id': arg.any_value()},
                    queue_name='live-site-playlists'
                )
                .next_call()
                .with_args(
                    url=reverse('playlists.send_track_to_live365'),
                    params={'id': arg.any_value()}
                )
                .next_call()
                .with_args(
                    url=reverse('playlists.play_count'),
                    params={'id': arg.any_value()}
                ))

        resp = self.client.post(reverse('playlists_add_event'), {
            'artist': "Squarepusher",
            'song': "Port Rhombus",
            "album": "Port Rhombus EP",
            "label": "Warp Records",
            "song_notes": "Dark melody. Really nice break down into half time."
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
        self.assertEquals(tracks[0].notes,
                "Dark melody. Really nice break down into half time.")

    @fudge.patch('playlists.tasks.taskqueue')
    def test_add_tracks_to_existing_stream(self, fake_tq):
        fake_tq.is_a_stub()
        # add several tracks:
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
        assert '<span class="artist">Def Leoppard</span>' in resp.content
        assert '<span class="artist">Steely Dan</span>' in resp.content

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

    @fudge.patch('playlists.tasks.taskqueue')
    def test_add_track_linked_to_library(self, fake_tq):
        fake_tq.is_a_stub()
        stevie = Artist.all().filter("name =", "Stevie Wonder")[0]
        talking_book = Album.all().filter("title =", "Talking Book")[0]
        sunshine = Track.all().filter("title =", "You Are The Sunshine Of My Life")[0]

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

    def setUp(self):
        super(TestLiveSitePlaylistTasks, self).setUp()
        self.recent_url = 'http://__push/recently-played'
        self.now_url = 'http://__push/now-playing'
        dbconfig['chirpradio.push.recently-played'] = self.recent_url
        dbconfig['chirpradio.push.now-playing'] = self.now_url

    @fudge.patch('playlists.tasks.urlfetch.fetch')
    def test_create(self, fetch):
        recent = fetch.expects_call().with_args(self.recent_url)
        recent.returns_fake().has_attr(status_code=200)
        now = recent.next_call().with_args(self.now_url)
        now.returns_fake().has_attr(status_code=200)

        resp = self.client.post(reverse('playlists.send_track_to_live_site'), {
            'id': self.track.key()
        })

    @fudge.patch('playlists.tasks.urlfetch.fetch')
    def test_create_failure(self, fetch):
        (fetch.expects_call().returns_fake()
                             .has_attr(status_code=500,
                                       content='busted'))
        resp = self.client.post(reverse('playlists.send_track_to_live_site'), {
            'id': self.track.key()
        })
        eq_(resp.status_code, 500)


class TestPlayCountTask(TaskTest, TestCase):

    def setUp(self):
        super(TestPlayCountTask, self).setUp()

    def count(self, track_key=None):
        if not track_key:
            track_key = self.track.key()
        return self.client.post(reverse('playlists.play_count'), {
            'id': track_key
        })

    def test_count(self):
        self.count()
        # Copy the same artist/track into a new track.
        new_trk = PlaylistTrack(
            playlist=self.track.playlist,
            selector=self.track.selector,
            freeform_artist_name=self.track.freeform_artist_name,
            freeform_album_title=self.track.freeform_album_title,
            freeform_track_title=self.track.freeform_track_title)
        new_trk.put()
        self.count()
        count = PlayCount.all()[0]
        eq_(count.artist_name, self.track.freeform_artist_name)
        eq_(count.album_title, self.track.freeform_album_title)
        eq_(count.play_count, 2)

    def test_count_different_track(self):
        self.count()
        # Copy the same artist/track into a new track.
        new_trk = PlaylistTrack(
            playlist=self.track.playlist,
            selector=self.track.selector,
            freeform_artist_name=self.track.freeform_artist_name,
            freeform_album_title=self.track.freeform_album_title,
            freeform_track_title='Another track from the album')
        new_trk.put()
        self.count()
        count = PlayCount.all()[0]
        eq_(count.artist_name, self.track.freeform_artist_name)
        eq_(count.album_title, self.track.freeform_album_title)
        eq_(count.play_count, 2)


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

class IsFromStudioTests(TestCase):
    """Test the FromStudioMiddleware playlists middleware."""

    def setUp(self):
        assert self.client.login(email="test@test.com", roles=[roles.DJ])
        dbconfig['chirp.studio_ip_range'] = '192.168.0.1,192.168.0.2'

    def test_warning_present_when_offsite(self):
        resp = self.client.get('/playlists/', {}, REMOTE_ADDR='127.0.0.1')
        assert 'name="is_from_studio_override"' in resp.content

    def test_warning_not_present_when_in_studio(self):
        resp = self.client.get('/playlists/', {}, REMOTE_ADDR='192.168.0.2')
        assert 'name="is_from_studio_override"' not in resp.content

    def test_override_post_sets_cookie(self):
        resp = self.client.get('/playlists/', {}, REMOTE_ADDR='127.0.0.1')
        resp = self.client.post('/playlists/', {'is_from_studio_override': 'override'})
        assert  'is_from_studio' in self.client.cookies.keys()

    def test_cookie_is_set_when_in_studio(self):
        resp = self.client.get('/playlists/', {}, REMOTE_ADDR='192.168.0.2')
        assert  'is_from_studio' in self.client.cookies.keys()

    def test_cookie_not_set_when_offsite(self):
        resp = self.client.get('/playlists/', {}, REMOTE_ADDR='127.0.0.1')
        assert 'is_from_studio' not in self.client.cookies.keys()

    def tearDown(self):
        clear_data()
        fudge.clear_expectations()
