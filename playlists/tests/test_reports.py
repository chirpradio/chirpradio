
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

from StringIO import StringIO
import csv
import datetime
from datetime import timedelta
import time

from django.core.urlresolvers import reverse

from auth import roles
from playlists import views as playlists_views
from playlists.models import Playlist, PlaylistTrack, PlaylistBreak, ChirpBroadcast
from playlists.tests.test_views import PlaylistViewsTest
from playlists.tests.test_views import create_stevie_wonder_album_data

__all__ = ['TestPlaylistReport']

class TestPlaylistReport(PlaylistViewsTest):

    def setUp(self):
        super(TestPlaylistReport, self).setUp()
        self.client.login(email="test@test.com", roles=[roles.DJ, roles.MUSIC_DIRECTOR])

    def test_report_landing_page(self):
        # sanity check:
        response = self.client.get(reverse('playlists_report'))

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
