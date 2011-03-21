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

    def __init__(self, transaction=None):
        # A cache of our pending, to-be-written SearchMatches objects.
        self._matches = {}
        # Additional objects to save at the same time as the
        # SearchMatches.
        self._txn_objects_to_save = []
        if transaction:
            self._transaction = transaction
        else:
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

    def _get_matches(self, entity_kind, field, term, key=None):
        """Returns a cached SearchMatches object for a given kind and term."""
        _key = (entity_kind, field, term)
        sm = self._matches.get(_key)
        if sm is None:
            if key:
                q = models.SearchMatches.all()
                q.filter("entity_kind =", entity_kind)
                q.filter("field =", field)
                q.filter("term =", term)
                q.filter("matches =", key)
                sms = q.fetch(1)
                if sms :
                    sm = sms[0]
            if sm is None:
                sm = models.SearchMatches(generation=_GENERATION,
                                          entity_kind=entity_kind,
                                          field=field,
                                          term=term,
                                          parent=self.transaction)
            self._matches[_key] = sm
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
        if album.label is not None:
            self.add_key(album.key(), "label", album.label)
        if album.year is not None:
            self.add_key(album.key(), "year", unicode(album.year))
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

    def remove_key(self, key, field, text):
        for term in set(explode(text)):
            sm = self._get_matches(key.kind(), field, term, key)
            sm.matches.remove(key)
            if not sm.matches:
                # Remove empty search index from datastore.
                AutoRetry(db).delete(sm)

                # Remove cached entry.
                _key = (key.kind(), field, term)
                if _key in self._matches:
                    del self._matches[_key]
                    
    def update_key(self, key, field, old_text, text):
        """Update index content associated with a datastore key.
        
        Args:
          key: A db.Key instance.
          field: A field identifier string.
          old_text: A unicode string, the old text, to be updated with text.
          text: A unicode string, the content to be indexed.
        """
        # Remove old terms.
        for term in set(explode(old_text)):
            sm = self._get_matches(key.kind(), field, term, key)
            if key in sm.matches:
                sm.matches.remove(key)
            
        # Add new terms.
        if text is not None:
            self.add_key(key, field, text)

    def update_artist(self, artist, fields):
        """Update index metadata associated with an Artist instance.
        
        Args:
          artist: An Artist instance.
          fields: A dictionary of field/property names to update and new values.
          
        artist must have the indexer's transaction as its parent key.
        artist is saved when the indexer's save() method is called.
        """
        assert artist.parent_key() == self.transaction
        for field, value in fields.iteritems():
            self.update_key(artist.key(), field, unicode(getattr(artist, field)), unicode(value))
            setattr(artist, field, value)
        self._txn_objects_to_save.append(artist)

    def update_album(self, album, fields):
        """Update index metadata associated with an Album instance.
        
        Args:
          album: An Album instance.
          fields: A dictionary of field/property names to update and new values.
          
        album must have the indexer's transaction as its parent key.
        album is saved when the indexer's save() method is called.
        """
        assert album.parent_key() == self.transaction
        for field, value in fields.iteritems():
            self.update_key(album.key(), field, unicode(getattr(album, field)), unicode(value))
            setattr(album, field, value)
        self._txn_objects_to_save.append(album)

    def update_track(self, track, fields):
        """Update index metadata associated with a Track instance.

        Args:
            track: A Track instance.
            fields: A dictionary of field/properties to update and new values.

        track must have the indexer's transaction as its parent key.
        track is saved when the indexer's save() method is called.
        """
        assert track.parent_key() == self.transaction
        for field, value in fields.iteritems():
            self.update_key(track.key(), field, unicode(getattr(track, field)), unicode(value))
            setattr(track, field, value)
        self._txn_objects_to_save.append(track)

    def save(self, rpc=None):
        """Write all pending index data into the Datastore."""
        self._txn_objects_to_save.extend(self._matches.itervalues())
        # All of the objects in self._txn_objects_to_save are part of
        # the same entity group.  This ensures that db.save is an
        # atomic operation --- either all of the objects are
        # successfully saved or none are.
        kwargs = {}
        if rpc is not None:
            kwargs["rpc"] = rpc
        AutoRetry(db).save(self._txn_objects_to_save, **kwargs)
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
IS_RANGE = "2:is_range"

def _parse_query_string(query_str):
    """Convert a query string into a sequence of annotated terms.

    Our query language is very simple:
      (1) "foo bar" means "find all entities whose text contains both
          the terms "foo" and "bar".
      (2) "-foo" means "exclude all entities whose text contains
          the term "foo".
      (3) "foo*" means "find all entities whose text contains a term starting
          with the prefix "foo".
      (4) "label:blah" means "find all entities whose given field (e.g., label)
          contains the given term.
      (5) "label:blah*" means "find all entities whose given field (e.g., label)
          starts with the prefix "blah".
      (6) "year:1970-1979" means "find all entities whose given field (e.g., year)
          falls within the range "1970" to "1979".

    We automatically filter out query terms that are stop words, as
    well as prefix-query terms that are also the prefix of a stop
    word.

    Returns:
      A sequence of tuples of rules, of the form
        (logic, flavor, arg, field, end)
      all of which are strings except for field and end.

      If logic == IS_REQUIRED, text must match the rule to be returned.
      If logic == IS_FORBIDDEN, text must not match the rule to be returned.
      If flavor == IS_TERM, arg is a term string.  
      If flavor == IS_PREFIX, arg is a term prefix string.
      If flavor == IS_RANGE, arg is a range of values.
      
      field (can be None) is the name of a field to search on.
      end (can be None) is the last term in a series of terms
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

        # Check if a field:value is given.
        field_qp = qp.split(':')
        if len(field_qp) == 2:
            if is_prefix:
                flavor = IS_PREFIX
            else:
                flavor = IS_TERM
            if is_required:
                logic = IS_REQUIRED
            else:
                logic = IS_FORBIDDEN
            end = None
            field, qp = field_qp

            if not is_prefix or not _is_stop_word_prefix(qp):
                # Check if a range is given.
                start_end = qp.split('-')
                if len(start_end) == 2:
                    qp, end = start_end

                if not _is_stop_word(qp):
                    query.append((logic, flavor, scrub(qp), field, end))

        else:
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
                query.append((logic, flavor, subp, None, None))

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


def fetch_keys_for_one_term(term, entity_kind=None, field=None, end=None):
    """Find entity keys matching a single search term.

    Args:
      term: A unicode string containing a single search term.
      entity_kind: An optional string.  If given, the returned keys are
        restricted to entities of that kind.
      field: An optional string.  If given, the returned keys are restricted
        to matches for that particular field.
      end: An optional string. If given, the returned keys are restricted to
        matched within a range from term to end.

    Returns:
      A set of (db.Key, matching field) pairs.
    """
    query = models.SearchMatches.all()
    if entity_kind:
        query.filter("entity_kind =", entity_kind)
    if field:
        query.filter("field =", field)
    if end:
        query.filter("term >=", term)
        query.filter("term <", end + u"\uffff")
    else:
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
    for logic, flavor, arg, field, end in sorted(parsed):
        # Find all of the matches related to this component of the
        # query.
        if flavor == IS_TERM:
            these_matches = fetch_keys_for_one_term(arg, entity_kind, field, end)
        elif flavor == IS_PREFIX:
            these_matches = fetch_keys_for_one_prefix(arg, entity_kind, field)
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
        if entity and not getattr(entity, "revoked", False):
            by_kind = segmented.get(entity.kind())
            if by_kind is None:
                by_kind = segmented[entity.kind()] = []
            by_kind.append(entity)
    for val in segmented.itervalues():
        val.sort(key=lambda x: x.sort_key)
    return segmented


def _album_is_reviewed(album, user_key):
    """Check if an album has been reviewed.

    Args:
      album: An Album entity
      user_key: A stringified user key, or None.

    Returns:
      If user_key is None, returns True if and only if the album has
        any reviews at all.
      If user_key is not None, returns True if and only if the album
        has been reviewed by the specified user.
    """
    if user_key is None or user_key == "":
        return len(album.reviews) > 0
    for review in album.reviews:
        if str(review.author.key()) == user_key:
            return True
    return False


def _artist_has_reviewed_album(artist, user_key):
    """Check if an artist has an album that has been reviewed.

    Args:
      artist: An Artist entity.
      user_key: A stringified user key, or None.

    Returns:
      True if _album_is_reviewed(album, user_key) is True for any
      album by that artist, False otherwise.
    """
    artist_album_query = models.Album.all().filter(
        "album_artist =", artist)
    for album in artist_album_query:
        if _album_is_reviewed(album, user_key):
            return True
    return False


def _discard_items(target_list, num_to_discard):
    """Discards items from a list at random.

    Args:
      target_list: The list to discard items from a list.  The list is
        modified in-place.
      num_to_discard: The number of items to attempt to discard.

    Returns:
      Returns the number of items that were actually discarded.
      This number will be equal to len(target_list) if that value is
      less than num_to_discard.
    """
    if num_to_discard <= 0 or target_list is None:
        return 0
    num_to_discard = min(len(target_list), num_to_discard)
    for _ in xrange(num_to_discard):
        discarded = target_list.pop()
    return num_to_discard
        

def _enforce_results_limit_on_matches(segmented_matches, max_num_results):
    """If necessary, throw away results to avoid returning too many items.

    Args:
      segmented_matches: A dictionary mapping entity type strings to
        lists of matching entities.  This dict is modified in-place.
      max_num_results: The maximum number of items that may be returned.
        This function does nothing is max_num_results is None.
    
    If the dict contains too many items, they are thrown away
    semi-randomly: Track objects are discarded first, then Albums,
    and finally Artists.
    """
    if max_num_results is None:
        return
    num_results = sum([len(x) for x in segmented_matches.itervalues()])
    num_to_discard = num_results - max_num_results
    for kind in ("Track", "Album", "Artist"):
        these_matches = segmented_matches.get(kind)
        num_to_discard -= _discard_items(these_matches, num_to_discard)
        if these_matches is not None and len(these_matches) == 0:
            del segmented_matches[kind]
    

def simple_music_search(query_str, max_num_results=None, entity_kind=None,
                        reviewed=False, user_key=None):
    """A simple free-form search well-suited for the music library.

    Args:
      query_str: A unicode query string.
      max_num_results: The maximum number of items to return.  If the
        number of matches exceeds this, some items will be discarded.
        If None, all matches will be returned.
      entity_kind: An optional string.  If given, the returned keys are
        restricted to entities of that kind.
      reviewed: If True, only return albums and tracks associated with
        albums that have been reviewed.
      user_key: If set, only return items containing reviews by the
        specified user.

    Returns:
      A dict mapping object types to lists of entities.
    """
    # First, find all matching keys.
    all_matches = fetch_keys_for_query_string(query_str, entity_kind)

    # If we returned None, this is an invalid query.
    if all_matches is None:
        return None

    # If a user key is set, we are only interested in items that have
    # been reviewed.
    if user_key:
        reviewed = True

    # Next, filter out the keys for tracks that do not have a title match.
    # Allow search on the tag field for tracks.
    keys_to_fetch = []
    for key, fields in all_matches.iteritems():
        if key.kind() != "Track" or "title" in fields or "tag" in fields:
            keys_to_fetch.append(key)

    # Fetch all of the specified keys from the datastore and construct a
    # segmented dict of matches.
    segmented_matches = load_and_segment_keys(keys_to_fetch)

    # If necessary, filter out unreviewed matches.
    if reviewed:
        if "Track" in segmented_matches:
            segmented_matches["Track"] = [
                trk for trk in segmented_matches["Track"]
                if _album_is_reviewed(trk.album, user_key)]
        if "Album" in segmented_matches:
            segmented_matches["Album"] = [
                alb for alb in segmented_matches["Album"]
                if _album_is_reviewed(alb, user_key)]
        if "Artist" in segmented_matches:
            segmented_matches["Artist"] = [
                art for art in segmented_matches["Artist"]
                if _artist_has_reviewed_album(art, user_key)]

    # Now enforce any limit on the number of results.
    _enforce_results_limit_on_matches(segmented_matches, max_num_results)
                
    return segmented_matches
        
