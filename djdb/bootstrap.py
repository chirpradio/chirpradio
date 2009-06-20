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

"""Bootstraps some test data into the DJDB."""

import datetime
import random
from django import http
from common import in_prod
from djdb import models
from djdb import search


_ARTIST_NAMES = (
    u"Bowie, David",
    u"Byrne, David",
    u"Fall, The",
    u"Fiery Furnaces, The",
    u"Kinks, The",
)

_WORDS = (
    "alpha", "beta", "gamma", "delta", "epsilon", "sigma", "theta",
    "dog", "cat", "monkey", "elephant", "bear", "hedgehog", "sloth",
    "orange", "yellow", "blue", "red", "black", "green", "pink", "purple",
    "bowie", "fall", "kinks",
    )


def random_phrase():
    return u" ".join(
        random.sample(_WORDS, random.randint(2, 5)))


def bootstrap(request):
    """Inject test library data into the datastore."""
    # We never want to do this in prod!
    if in_prod():
        return http.HttpResponse(status=403)
    # First, inject the artist names.
    search.create_artists(_ARTIST_NAMES)
    # Now build up a bunch of random albums for each artist.
    counter = 1
    idx = search.Indexer()
    for art in models.Artist.all().fetch(100):
        for _ in range(random.randint(1, 10)):

            # 10% are multi-disc sets
            discs = [None]
            if random.randint(1, 10) == 1:
                discs = range(1, random.randint(2, 5))

            for disc_num in discs:
                counter += 1
                alb = models.Album(
                    title=random_phrase(),
                    disc_number=disc_num,
                    album_id=counter,
                    import_timestamp=datetime.datetime.now(),
                    album_artist=art,
                    num_tracks=random.randint(2, 12),
                    )
                alb.save()
                idx.add_album(alb)
                for i in range(alb.num_tracks):
                    trk = models.Track(
                        ufid="%d:%d" % (counter, i),
                        album=alb,
                        title=random_phrase(),
                        track_num=i+1,
                        sampling_rate_hz=44100,
                        bit_rate_kbps=128,
                        channels=u"stereo",
                        duration_ms=random.randint(60000, 300000))
                    trk.save()
                    idx.add_track(trk)
                idx.save()
    return http.HttpResponseRedirect("/djdb/")
