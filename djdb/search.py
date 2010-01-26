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
from common.autoretry import AutoRetry

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
_STOP_WORDS = set(['and', 'in', 'is', 'it', 'my', 'of', 'the', 'to'])


def _is_stop_word(term):
    return len(term) <= 1 or term in _STOP_WORDS


def _is_stop_word_prefix(prefix):
    return any(sw.startswith(prefix) for sw in _STOP_WORDS)


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
        # Additional objects to save at the same time as the
        # SearchMatches.
        self._txn_objects_to_save = []
        # We use the current time in microseconds as the transaction ID.
        timestamp = int(1000000*time.time())
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
        """Prepare to index metadata associated with an Artist instance.

        artist must have the indexer's transaction as its parent key.
        artist is saved when the indexer's save() method is called.
        """
        assert artist.parent_key() == self.transaction
        self.add_key(artist.key(), "name", artist.name)
        self._txn_objects_to_save.append(artist)

    def add_album(self, album):
        """Prepare to index metdata associated with an Album instance.

        album must have the indexer's transaction as its parent key.
        album is saved when the indexer's save() method is called.
        """
        assert album.parent_key() == self.transaction
        self.add_key(album.key(), "title", strip_tags(album.title))
        self.add_key(album.key(), "artist", album.artist_name)
        self._txn_objects_to_save.append(album)

    def add_track(self, track):
        """Prepare to index metdata associated with a Track instance.

        track must have the indexer's transaction as its parent key.
        track is saved when the indexer's save() method is called.
        """
        assert track.parent_key() == self.transaction
        self.add_key(track.key(), "title", strip_tags(track.title))
        self.add_key(track.key(), "album", strip_tags(track.album.title))
        self.add_key(track.key(), "artist", track.artist_name)
        self._txn_objects_to_save.append(track)

    def save(self):
        """Write all pending index data into the Datastore."""
        self._txn_objects_to_save.extend(self._matches.itervalues())
        # All of the objects in self._txn_objects_to_save are part of
        # the same entity group.  This ensures that db.save is an
        # atomic operation --- either all of the objects are
        # successfully saved or none are.
        AutoRetry(db).save(self._txn_objects_to_save)
        self._matches = {}
        self._txn_objects_to_save


def optimize_index(term):
    """Optimize our index for a specific term.

    Locates all SearchMatches objects associated with the given term
    and merges them together so that there is only one SearchMatches
    per entity kind and field.

    Args:
      text: A normalized search term.

    Returns:
      The decrease in the number of SearchMatches objects as a result of
      the optimization.
    """
    query = models.SearchMatches.all().filter("term =", term)

    # First we iterate over all of the SearchMatches associated with
    # particular term and segment them by entity kind and field.
    segmented = {}
    for sm in AutoRetry(query).fetch(999):
        # Skip anything outside the current generation.
        if sm.generation != _GENERATION:
            continue
        key = (sm.entity_kind, sm.field)
        subset = segmented.get(key)
        if not subset:
            subset = segmented[key] = []
        subset.append(sm)

    num_deleted = 0

    # Is this term a stop word?  In that case we can just delete
    # everything that we found.  This case occurs when new stop words
    # are added to the list.
    if _is_stop_word(term):
        for subset in segmented.itervalues():
            db.delete(subset)
            num_deleted += len(subset)
        return num_deleted

    # Now for any segment that contains more than one SearchMatches object,
    # merge them all together.
    for (kind, field), subset in segmented.iteritems():
        if len(subset) > 1:
            merged = models.SearchMatches(generation=_GENERATION,
                                          entity_kind=kind,
                                          field=field,
                                          term=term)
            union_of_all_matches = set()
            for sm in subset:
                union_of_all_matches.update(sm.matches)
            merged.matches.extend(union_of_all_matches)
            # We have to be careful about how we make the change in the
            # datastore: we write out the new merged object first and
            # then delete the old objects.  That ensures that no matches
            # will be lost if any operation fails.
            merged.save()  # Save the new matches
            db.delete(subset)  # Delete the old matches
            # The -1 accounts for the new SearchMatches object that
            # we created.
            num_deleted += len(subset) - 1

    return num_deleted


def create_artists(all_artist_names):
    """Adds a set of artists to the datastore inside of a transaction.

    Args:
      all_artist_names: A sequence of unicode strings, which are the
        names of the artists to be added.
    """
    idx = Indexer()
    artist_objs = []
    for name in all_artist_names:
        art = models.Artist.create(name=name,
                                   parent=idx.transaction)
        idx.add_artist(art)
    AutoRetry(idx).save()


###
### Query String Parsing
###

# The 0: and 1: prefixes are used to force these symbols to sort into
# the desired order.
IS_REQUIRED = "0:is_required"
IS_FORBIDDEN = "1:is_forbidden"

IS_TERM = "0:is_term"
IS_PREFIX = "1:is_prefix"

def _parse_query_string(query_str):
    """Convert a query string into a sequence of annotated terms.

    Our query language is very simple:
      (1) "foo bar" means "find all entities whose text contains both
          the terms "foo" and "bar".
      (2) "-foo" means "exclude all entities whose text contains
          the term "foo".
      (3) "foo*" means "find all entities whose text contains a term starting
          with the prefix "foo".

    We automatically filter out query terms that are stop words, as
    well as prefix-query terms that are also the prefix of a stop
    word.

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
                # We need to filter out any prefix which might match a
                # stop word.  Otherwise a prefix search like "mott
                # th*" would fail to match "Mott the Hoople".
                if _is_stop_word_prefix(subp):
                    continue
                flavor = IS_PREFIX
            # Skip stop words when building a query 
            # because no stop words exist in the index.
            if _is_stop_word(subp):
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
    """Returns a set of (db.Key, matching field) pairs."""
    # For now, we don't actually return all results --- just the
    # results we can gather from the first 999 match objects.
    # That should always be enough.
    all_matches = set()
    for sm in AutoRetry(query).fetch(limit=999):
        # Ignore objects that are not in the current generation.
        if sm.generation != _GENERATION:
            continue
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
    for entity in AutoRetry(db).get(fetched_keys):
        if entity:
            by_kind = segmented.get(entity.kind())
            if by_kind is None:
                by_kind = segmented[entity.kind()] = []
            by_kind.append(entity)
    for val in segmented.itervalues():
        val.sort(key=lambda x: x.sort_key)
    return segmented

def simple_music_search(query_str, max_num_results=None, entity_kind=None, reviewed=False, user_key=None):
    """A simple free-form search well-suited for the music library.

    Args:
      query_str: A unicode query string.
      max_num_results: The maximum number of items to return.  If the
        number of matches exceeds this, some items will be discarded.
        If None, all matches will be returned.
      entity_kind: An optional string.  If given, the returned keys are
        restricted to entities of that kind.
      reviewed: Boolean indicating whether to return albums and tracks associated with albums that
        have been reviewed.

    Returns:
      A dict mapping object types to lists of entities.
    """
    # First, find all matching keys.
    all_matches = fetch_keys_for_query_string(query_str, entity_kind)

    # If we returned None, this is an invalid query.
    if all_matches is None:
        return None

    # Next, filter out all tracks that do not have a title match.
    # Also filter reviewed albums.
    filtered = []
    recordcount = 0
    for key, fields in all_matches.iteritems():
        filter = True
        if key.kind() == "Track" :
            album = AutoRetry(db).get(key).album
            if reviewed and len(album.reviews) == 0:
                filter = False
            elif reviewed and user_key:
                filter = False
                for review in album.reviews :
                    if str(review.author.key()) == user_key :
                        filter = True
                        break
                        
        elif key.kind() == "Album" :
            album = AutoRetry(db).get(key)
            if reviewed and len(album.reviews) == 0:
                filter = False
            elif reviewed and user_key:
                filter = False
                for review in album.reviews :
                    if str(review.author.key()) == user_key :
                        filter = True
                        break
            
        elif key.kind() == "Artist" :
            artist = AutoRetry(db).get(key)
            if reviewed:
                filter = False
                for album in models.Album.all().filter("album_artist =", artist) :
                    if len(album.reviews) != 0:
                        if user_key:
                            for review in album.reviews:
                                if str(review.author.key()) == user_key:
                                    filter = True
                                    break
                        else:
                            filter = True
                
        if filter and (key.kind() != "Track" or "title" in fields):
            recordcount += 1
            # If we got too many matches, throw some away.
            if max_num_results and recordcount > max_num_results:
                break
            filtered.append(key)

    # Finally, return a segmented dict of matches.
    return load_and_segment_keys(filtered)
        
