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

import datetime
from google.appengine.ext import db
from djdb import models
from djdb import search


_ALBUM_LINE_PREFIX = "ALB"
_TRACK_LINE_PREFIX = "TRK"


def _lookup_artist(name, cache_dict):
    if name in cache_dict:
        return cache_dict[name]
    q = models.Artist.all().filter("name =", name)
    for art in q.fetch(1):
        cache_dict[name] = art
        return art
    return None


def _decode_album_line(line, txn, cache_dict):
    parts = line.split("\0")
    assert len(parts) == 6
    assert parts[0] == _ALBUM_LINE_PREFIX
    kwargs = {}
    kwargs["parent"] = txn
    kwargs["title"] = parts[1].decode("utf-8")
    kwargs["album_id"] = int(parts[2])
    timestamp = int(parts[3])
    kwargs["import_timestamp"] = datetime.datetime.utcfromtimestamp(timestamp)
    if parts[4]:
        art =  _lookup_artist(parts[4].decode("utf-8"), cache_dict)
        assert art is not None
        kwargs["album_artist"] = art
    else:
        kwargs["is_compilation"] = True
    kwargs["num_tracks"] = int(parts[5])
    return models.Album(**kwargs)


def _decode_track_line(line, album, cache_dict):
    parts = line.split("\0")
    assert len(parts) == 9
    assert parts[0] == _TRACK_LINE_PREFIX
    kwargs = {}
    kwargs["parent"] = album.parent_key()
    kwargs["album"] = album
    kwargs["ufid"] = parts[1]
    kwargs["title"] = parts[2].decode("utf-8")
    if parts[3]:
        art = _lookup_artist(parts[3].decode("utf-8"), cache_dict)
        assert art is not None
        kwargs["track_artist"] = art
    kwargs["track_num"] = int(parts[4])
    kwargs["sampling_rate_hz"] = int(parts[5])
    kwargs["bit_rate_kbps"] = int(parts[6])
    kwargs["channels"] = parts[7].decode("utf-8")
    kwargs["duration_ms"] = int(parts[8])
    return models.Track(**kwargs)


def decode_and_save(data):
    cache_dict = {}
    idx = search.Indexer()
    current_album = None
    objects = []
    for line in data.splitlines():
        if not line: continue  # Skip blank lines
        if line.startswith(_ALBUM_LINE_PREFIX):
            current_album = _decode_album_line(line, idx.transaction,
                                               cache_dict)
            objects.append(current_album)
            idx.add_album(current_album)
        else:
            assert current_album is not None
            trk = _decode_track_line(line, current_album, cache_dict)
            objects.append(trk)
            idx.add_track(trk)

    def transaction_fn():
        db.save(objects)
        idx.save()
    db.run_in_transaction(transaction_fn)
