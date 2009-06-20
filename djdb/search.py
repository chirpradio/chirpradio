# -*- coding: utf-8 -*-

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
import re
import time
import unicodedata
from google.appengine.ext import db
from djdb import models

# All search data used by this code is marked with this generation.
_GENERATION = 1


###
### Text Normalization
###

# This mapping is used when normalizing characters when indexing text
# and processing search queries.
_CHARACTER_NORMALIZATIONS = {
    u'ø': 'o',
}


# These words are ignored when indexing text and processing search
# queries.
_STOP_WORDS = set(["the", "and", "of"])


def _is_stop_word(term):
    return len(term) <= 1 or term in _STOP_WORDS


def _scrub_char(c):
    """Normalize a character for use in indexing and searching.
    
    Among other things, this removes diacritics and strips out punctuation.
    """
    c = c.lower()
    if unicodedata.category(c)[0] in ("L", "N"):
        c = unicodedata.normalize("NFD", c)[0]
        return _CHARACTER_NORMALIZATIONS.get(c, c)
    elif c == "'":
        # Filter out apostrophes, so "foo's" will become "foos".
        return ""
    else:
        # Other types of characters are replaced by whitespace.
        return " "


# This matches interior periods, i.e. "L.A"
_COLLAPSE_INTERIOR_PERIODS_RE = re.compile(r"(\S)\.(\S)")

def scrub(text):
    """Normalizes a text string for use in indexing and searching."""
    # Strip out interior periods.
    text = _COLLAPSE_INTERIOR_PERIODS_RE.sub(r"\1\2", text)
    chars = [_scrub_char(c) for c in text]
    return "".join(chars)


def explode(text):
    """Splits a piece of text into a normalized list of terms.

    Stop words are stripped out, along with any other
    un-indexable/searchable content.
    """
    return [term for term in scrub(text).split() if not _is_stop_word(term)]


def strip_tags(text):
    """Removes all tags from a string.

    A tag is a chunk of text enclosed in square bracks, [like this].
    """
    return re.sub(r"\[[^\]]+\]", "", text)


###
### Indexing
###

class Indexer(object):
    """Builds a searchable index of text associated with datastore entities."""

    def __init__(self):
        # A cache of our pending, to-be-written SearchMatches objects.
        self._matches = {}
        # We use the current time in microseconds as the transaction ID.
        timestamp = 1000000*int(time.time())
        self._transaction = db.Key.from_path("IndexerTransaction",
                                             timestamp)

    @property
    def transaction(self):
        """Transaction used for all created SearchMatches objects.

        We expose this so that entities being indexed can be created inside
        the same transaction, allowing both the objects and the index data
        to be written into the datastore in an atomic operation.
        """
        return self._transaction

    def _get_matches(self, entity_kind, field, term):
        """Returns a cached SearchMatches object for a given kind and term."""
        key = (entity_kind, field, term)
        sm = self._matches.get(key)
        if sm is None:
            sm = models.SearchMatches(generation=_GENERATION,
                                      entity_kind=entity_kind,
                                      field=field,
                                      term=term,
                                      parent=self.transaction)
            self._matches[key] = sm
        return sm

    def add_key(self, key, field, text):
        """Prepare to index content associated with a datastore key.

        Args:
          key: A db.Key instance.
          field: A field identifier string.
          text: A unicode string, the content to be indexed.
        """
        for term in set(explode(text)):
            sm = self._get_matches(key.kind(), field, term)
            sm.matches.append(key)

    def add_artist(self, artist):
        """Prepare to index metadata associated with an Artist instance."""
        self.add_key(artist.key(), None, artist.name)

    def add_album(self, album):
        """Prepare to index metdata associated with an Album instance."""
        self.add_key(album.key(), "title", strip_tags(album.title))
        self.add_key(album.key(), "artist", album.artist_name)

    def add_track(self, track):
        """Prepare to index metdata associated with a Track instance."""
        self.add_key(track.key(), "title", strip_tags(track.title))
        self.add_key(track.key(), "album", strip_tags(track.album.title))
        self.add_key(track.key(), "artist", track.artist_name)

    def save(self):
        """Write all pending index data into the Datastore."""
        db.save(self._matches.values())
        self._matches = {}


def create_artists(all_artist_names):
    """Adds a set of artists to the datastore inside of a transaction.

    Args:
      all_artist_names: A sequence of unicode strings, which are the
        names of the artists to be added.
    """
    idx = Indexer()

    def transaction_fn():
        artist_objs = []
        for name in all_artist_names:
            art = models.Artist.create(name=name,
                                       parent=idx.transaction)
            artist_objs.append(art)
            idx.add_artist(art)
        db.save(artist_objs)
        idx.save()

    db.run_in_transaction(transaction_fn)


###
### Query String Parsing
###

# The 0: and 1: prefixes are used to force these symbols to sort into
# the desired order.
IS_REQUIRED = "0:is_required"
IS_FORBIDDEN = "1:is_forbidden"

IS_TERM = "is_term"
IS_PREFIX = "is_prefix"

def _parse_query_string(query_str):
    """Convert a query string into a sequence of annotated terms.

    Our query language is very simple:
      (1) "foo bar" means "find all entities whose text contains both
          the terms "foo" and "bar".
      (2) "-foo" means "exclude all entities whose text contains
          the term "foo".
      (3) "foo*" means "find all entities whose text contains a term starting
          with the prefix "foo".

    Returns:
      A sequence of 3-tuples of rules, of the form
        (logic, flavor, arg)
      all of which are strings.

      If logic == IS_REQUIRED, text must match the rule to be returned.
      If logic == IS_FORBIDDEN, text must not match the rule to be returned.
      If flavor == IS_TERM, arg is a term string.  
      If flavor == IS_PREFIX, arg is a term prefix string.
     
    """
    query_str_parts = query_str.split()
    query = []
    for qp in query_str_parts:
        is_required = True
        is_prefix = False
        if qp.startswith("-"):
            is_required = False
            qp = qp.lstrip("-")
        if qp.endswith("*"):
            is_prefix = True
            qp = qp.rstrip("*")
        subparts = scrub(qp).split()
        for i, subp in enumerate(subparts):
            flavor = IS_TERM
            logic = IS_REQUIRED
            if i == 0 and not is_required:
                logic = IS_FORBIDDEN
            if i == len(subparts)-1 and is_prefix:
                flavor = IS_PREFIX
            # Skip stop words, but only in the case of a full term.
            # The use of a stop word as a prefix (e.g. the query "the*")
            # is allowed.
            if flavor == IS_TERM and _is_stop_word(subp):
                continue
            # Skip parts where the search term or prefix is empty.
            if not subp:
                continue
            query.append((logic, flavor, subp))

    return query


###
### Searching
###

def _fetch_all(query):
    # For now, we don't actually return all results --- just the
    # results we can gather from the first 999 match objects.
    # That should always be enough.
    all_matches = set()
    for sm in query.fetch(limit=999):
        all_matches.update((m, sm.field) for m in sm.matches)
    return all_matches


def fetch_keys_for_one_term(term, entity_kind=None, field=None):
    """Find entity keys matching a single search term.

    Args:
      term: A unicode string containing a single search term.
      entity_kind: An optional string.  If given, the returned keys are
        restricted to entities of that kind.
      field: An optional string.  If given, the returned keys are restricted
        to matches for that particular field.

    Returns:
      A set of (db.Key, matching field) pairs.
    """
    query = models.SearchMatches.all()
    if entity_kind:
        query.filter("entity_kind =", entity_kind)
    if field:
        query.filter("field =", field)
    query.filter("term =", term)
    return _fetch_all(query)


def fetch_keys_for_one_prefix(term_prefix, entity_kind=None, field=None):
    """Find entity keys matching a single search term prefix.

    Args:
      term: A unicode string containing a single search term.
      entity_kind: An optional string.  If given, the returned keys are
        restricted to entities of that kind.
      field: An optional string.  If given, the returned keys are restricted
        to matches for that particular field.

    Returns:
      A set of (db.Key, matching field) pairs.
    """
    query = models.SearchMatches.all()
    if entity_kind:
        query.filter("entity_kind =", entity_kind)
    if field:
        query.filter("field =", field)
    query.filter("term >=", term_prefix)
    query.filter("term <", term_prefix + u"\uffff")
    return _fetch_all(query)


def fetch_keys_for_query_string(query_str, entity_kind=None):
    """Find entity keys matching a single search term prefix.

    Args:
      query_str: A unicode query string.
      entity_kind: An optional string.  If given, the returned keys are
        restricted to entities of that kind.

    Returns:
      A dict mapping db.Key objects to a set of matching fields.
    """
    parsed = set(_parse_query_string(query_str))
    # The empty query is invalid.
    if not parsed:
        return None
    all_matches = {}
    is_first = True
    # We sort the parsed query so that all of the terms with
    # logic=IS_REQUIRED will be processed first.
    for logic, flavor, arg in sorted(parsed):
        # Find all of the matches related to this component of the
        # query.
        if flavor == IS_TERM:
            these_matches = fetch_keys_for_one_term(arg, entity_kind)
        elif flavor == IS_PREFIX:
            these_matches = fetch_keys_for_one_prefix(arg, entity_kind)
        else:
            # This should never happen.
            logging.error("Query produced unexpected results: %s", query_str)
            return None
        # Now use this component's matches to update the complete set.
        if logic == IS_REQUIRED:
            if is_first:
                for m, f in these_matches:
                    all_matches[m] = set([f])
            else:
                new_all_matches = {}
                for m, f in these_matches:
                    existing_fs = all_matches.get(m)
                    if existing_fs:
                        new_all_matches[m] = set([f]).union(existing_fs)
                all_matches = new_all_matches
        elif logic == IS_FORBIDDEN:
            if is_first:
                # The first thing we see should not be a negative query part.
                # If so, the query is invalid.
                return None
            for m, _ in these_matches:
                if m in all_matches:
                    del all_matches[m]
        else:
            # This should never happen.
            logging.error("Query produced unexpected results: %s", query_str)
            return None
        is_first = False
        # Is our set of matches empty?  If so, there is no point in
        # processing any more terms.
        if not all_matches:
            break
    return all_matches


def load_and_segment_keys(fetched_keys):
    """Convert a series of datastore keys into a dict of lists of entities.

    Args:
      fetched_keys: A sequence of datastore keys, possibly returned by
        one of the above fetch_key_*() functions.

    Returns:
      A dict mapping entity kind names (which are strings) to
      lists of entities of that type.
    """
    segmented = {}
    for entity in db.get(fetched_keys):
        if entity:
            by_kind = segmented.get(entity.kind())
            if by_kind is None:
                by_kind = segmented[entity.kind()] = []
            by_kind.append(entity)
    return segmented


def simple_music_search(query_str):
    """A simple free-form search well-suited for the music library.

    Args:
      query_str: A unicode query string.

    """
    # First, find all matching keys.
    all_matches = fetch_keys_for_query_string(query_str)

    # If we returned None, this is an invalid query.
    if all_matches is None:
        return None

    # Next, filter out all tracks that do not have a title match.
    filtered = []
    for key, fields in all_matches.iteritems():
        if key.kind() != "Track" or "title" in fields:
            filtered.append(key)

    # Finally, return a segmented dict of matches.
    return load_and_segment_keys(filtered)
        
