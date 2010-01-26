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

"""Data model for CHIRP's DJ database."""

import hashlib

from google.appengine.ext import db

from auth.models import User
from common import sanitize_html
from common import time_util
from common.autoretry import AutoRetry


# A list of standard doctypes.
DOCTYPE_REVIEW = "review"  # A review, subject must be an Album object.
DOCTYPE_COMMENT = "comment" # An album comment, subject must be an Album object.

EXPLICIT_TAG = "explicit"
RECOMMENDED_TAG = "recommended"

# List of album categories.
ALBUM_CATEGORIES = ['core', 'local_current', 'local_classic', 'heavy', 'light']

class DjDbImage(db.Model):
    """An image (usually a JPEG or PNG) associated with an artist or album.

    Images are uniquely defined by their SHA1 checksums.

    Attributes:
      image_data: A binary blob containing the image data.
      image_mimetype: A string that describes the image's mimetype.
    """

    image_data = db.BlobProperty(required=True)

    image_mimetype = db.StringProperty(required=True)

    _KEY_PREFIX = u"djdb/img:"

    @classmethod
    def get_key_name(cls, sha1):
        """Returns the datastore key name based on the image's SHA1."""
        return cls._KEY_PREFIX + sha1

    def __init__(self, *args, **kwargs):
        """Constructor.

        If necessary, automatically sets the entity's key according
        to our standard scheme.
        """
        if 'sha1' in kwargs:
            assert 'key_name' not in kwargs
            kwargs['key_name'] = self.get_key_name(kwargs['sha1'])
        db.Model.__init__(self, *args, **kwargs)

    @property
    def sha1(self):
        """Returns the image's SHA1 checksum."""
        return self.key().name()[len(self._KEY_PREFIX):]

    URL_PREFIX = "/djdb/image/"

    @property
    def url(self):
        """Returns a URL that can be used to retrieve this image."""
        return self.URL_PREFIX + self.sha1

    @classmethod
    def get_by_url(cls, url):
        """Fetches an image from the datastore by URL.

        Returns None if no matching image can be found.
        """
        i = url.find(cls.URL_PREFIX)
        if i == -1:
            return None
        sha1 = url[i + len(cls.URL_PREFIX):]
        key_name = cls.get_key_name(sha1)
        return AutoRetry(cls).get_by_key_name(key_name)

class Artist(db.Model):
    """An individual musician, or a band.

    These entities are uploaded directly from the CHIRP music library
    database, which is considered to be authoritative.

    Attributes:
      name: The canonical name used to describe this artist in TPE1 tags.
        This name should follow the music committee's naming style guide.
      image: An image associated with this artist.
    """
    name = db.StringProperty(required=True)

    image = db.ReferenceProperty(DjDbImage)

    # TODO(trow): Add a list of references to related artists?

    @classmethod
    def create(cls, *args, **kwargs):
        """Create an Artist object with an automatically-assigned key."""
        if 'key_name' not in kwargs:
            encoded_name = kwargs['name'].encode('utf-8')
            hashed = hashlib.sha1(encoded_name).hexdigest()
            kwargs['key_name'] = "artist:%s" % hashed
        return cls(*args, **kwargs)

    @classmethod
    def fetch_by_name(cls, name):
        """Fetch a single Artist by name."""
        name = name and name.strip()
        if not name:
            return None
        for art in AutoRetry(cls.all().filter("name =", name)).fetch(1):
            return art
        return None

    @classmethod
    def fetch_all(cls):
        """Yields all artists, in a random order."""
        q = cls.all().order("__key__")
        while True:
            batch = list(q.fetch(500))
            if not batch:
                break
            for art in batch:
                yield art
            q = cls.all().order("__key__").filter("__key__ >", batch[-1].key())

    @property
    def pretty_name(self):
        """Returns a slightly prettier version of an artist's name."""
        if self.name.endswith(", The"):
            return "The " + self.name[:-5]
        return self.name

    def __unicode__(self):
        return self.pretty_name

    @property
    def sort_key(self):
        """A key that can be used for sorting.

        Included here for symmetry with the other object types.
        """
        return self.name

    @property
    def sorted_albums(self):
        """Sorted list of albums by this artist."""
        return sorted(self.album_set, key=lambda x: x.sort_key)

    @property
    def sorted_tracks(self):
        """Sorted list of tracks by this artist.

        These are tracks that appear on compilations.  It does not
        include tracks on albums that are specifically by this artist.
        """
        return sorted(self.track_set, key=lambda x: x.sort_key)

    @property
    def url(self):
        """URL for artist information page."""
        return u"/djdb/artist/%s/info" % self.name

    @property
    def num_albums(self):
        """Returns the number of albums by this artist."""
        # This should be a bit more efficient than looking at the
        # length of set.album_set.
        return AutoRetry(Album.all().filter("album_artist =", self)).count()


class Album(db.Model):
    """An album in CHIRP's digital library.

    An album consists of a series of numbered tracks.

    Attributes:
      category: The category of the album. May be core, local_current, local_classic, heavy, light.
      title: The name of the album.  This is used in TALB tags.
      disc_number: If specified, this album is one part of a multi-disc
        set.
      album_id: A unique integer identifier that is assigned to the
        album when it is imported into the music library.
      import_timestamp: When this album was added to the library.
      is_compilation: If True, this album is a compilation and
        contains songs by many different artists.
      album_artist: A reference to the Artist entity of the creator
        of this album.  This attribute is set if and only if
        'is_compilation' is False.
      num_tracks: The number of tracks on this album.
      import_tags: A list of the tags that were attached to this album
        when it was imported into the library.
      image: An image associated with this album.  This is typically
        used for the album's cover art.
    """
    category = db.StringProperty(required=False)
    
    title = db.StringProperty(required=True)

    disc_number = db.IntegerProperty(required=False)

    album_id = db.IntegerProperty(required=True)

    import_timestamp = db.DateTimeProperty(required=True)

    is_compilation = db.BooleanProperty(required=False, default=False)

    album_artist = db.ReferenceProperty(Artist, required=False)

    num_tracks = db.IntegerProperty(required=True)

    import_tags = db.StringListProperty()

    # Do not manipulate this field directly!  Instead, use the
    # functions provided in the tag_util module.
    #
    # This is just a cached version of the data; the authoritative
    # version of the tags for 'obj' are found by calling
    # TagEdit.fetch_and_merge(obj).
    current_tags = db.StringListProperty()

    # This is just a cached version of the data; the authoritative
    # review count is generate by calling len(album.reviews).
    num_reviews = db.IntegerProperty(default=0)

    # This is a cached version of number of comments; the authoritative
    # comment count is generated by calling len(album.comments).
    num_comments = db.IntegerProperty(default=0)
    
    image = db.ReferenceProperty(DjDbImage)

    # Keys are automatically assigned. 
    _KEY_FORMAT = u"djdb/a:%x"

    @classmethod
    def get_key_name(cls, album_id):
        """Generate the datastore key for an Album entity."""
        return cls._KEY_FORMAT % album_id

    def __init__(self, *args, **kwargs):
        """Constructor.

        If necessary, automatically sets the entity's key according
        to our standard scheme.
        """
        if 'key_name' not in kwargs:
            kwargs['key_name'] = self.get_key_name(kwargs['album_id'])
        db.Model.__init__(self, *args, **kwargs)

    def __unicode__(self):
        return self.title

    @property
    def url(self):
        return "/djdb/album/%d/info" % self.album_id

    _COMPILATION_ARTIST_NAME = u"Various Artists"

    _MISSING_ARTIST_NAME = u"*MISSING ARTIST*"

    @property
    def artist_name(self):
        """Returns a human-readable string describing the album's creator."""
        if self.is_compilation:
            return self._COMPILATION_ARTIST_NAME
        return ((self.album_artist and self.album_artist.name)
                or self._MISSING_ARTIST_NAME)

    @property
    def artist_url(self):
        """Returns a URL for the artist information page for this album."""
        if self.album_artist:
            return self.album_artist.url
        # TODO(trow): Generate some sort of reasonable artist URL for
        # compilations.
        return "/sorry/not/yet/supported"

    @property
    def sort_key(self):
        """A key that can be used to sort Albums into a reasonable order."""
        title = self.title
        if title.lower().startswith("the "):
            title = title[:4]
        return (self.artist_name, title, self.disc_number)

    @property
    def sorted_tracks(self):
        """Returns Album tracks sorted by track number."""
        return sorted(self.track_set, key=lambda x: x.sort_key)

    @property
    def reviews(self):
        """Returns all reviews for this object."""
        rev_docs = [doc for doc in self.document_set
                    if doc.doctype == DOCTYPE_REVIEW]
        rev_docs.sort(key=lambda x: x.sort_key)
        return rev_docs

    @property
    def comments(self):
        """Returns all comments for this object."""
        comment_docs = [doc for doc in self.document_set
                        if doc.doctype == DOCTYPE_COMMENT]
        comment_docs.sort(key=lambda x: x.sort_key)
        return comment_docs

    @property
    def sorted_current_tags(self):
        """Returns a sorted list of tags."""
        return sorted(self.current_tags, key=unicode.lower)

    def has_tag(self, tag):
        """Returns true if tag 'tag' is currently set."""
        tag = tag.lower()
        return any(tag == t.lower() for t in self.current_tags)


_CHANNEL_CHOICES = ("stereo", "joint_stereo", "dual_mono", "mono")


class Track(db.Model):
    """A track in CHIRP's digital library.

    Each track's audio content is stored in a separate MP3 file in
    the digital library.

    Attributes:
      album: A reference to the Album entity that this track is a part of.
      title: The name of the track, as stored in the MP3 file's TIT2 tag.
      track_artist: A reference to the Artist entity of the track's creator.
        This must be set if self.album.is_compilation is True.
        It may be set if self.album.is_compilation is False.
      import_tags: A list of the tags that were attached to this track
        when it was imported into the library.
      sampling_rate_hz: The sampling rate of the track's MP3 file, measured
        in Hertz.
      bit_rate_kbps: The bit rate of the MP3 file, measured in kbps (kilobits
        per second).
      channels: The number and type of channels in the MP3 file.
      duration_ms: The duration of the track, measured in milliseconds.
        (Remember that 1 second = 1000 milliseconds!)
    """
    album = db.ReferenceProperty(Album, required=True)

    title = db.StringProperty(required=True)

    track_artist = db.ReferenceProperty(Artist, required=False)

    import_tags = db.StringListProperty()

    # Do not manipulate this field directly!  Instead, use the
    # functions provided in the tag_util module.
    #
    # This is just a cached version of the data; the authoritative
    # version of the tags for 'obj' are found by calling
    # TagEdit.fetch_and_merge(obj).
    current_tags = db.StringListProperty()

    # TODO(trow): Validate that this is > 0 and <= self.album.num_tracks.
    track_num = db.IntegerProperty(required=True)

    sampling_rate_hz = db.IntegerProperty(required=True)

    bit_rate_kbps = db.IntegerProperty(required=True)

    channels = db.CategoryProperty(required=True, choices=_CHANNEL_CHOICES)

    # TODO(trow): Validate that this is > 0.
    duration_ms = db.IntegerProperty(required=True)

    @property
    def duration(self):
        """A human-readable version of the track's duration."""
        dur_ms = self.duration_ms % 1000
        dur_s = ((self.duration_ms - dur_ms) // 1000) % 60
        dur_m = (self.duration_ms - dur_ms - 1000*dur_s) // 60000
        return "%d:%02d" % (dur_m, dur_s)

    @property
    def artist_name(self):
        """Returns a string containing the name of the track's creator."""
        return ((self.track_artist and self.track_artist.name)
                or self.album.artist_name)

    @property
    def artist_url(self):
        """Returns a URL for this track's artist's information."""
        return ((self.track_artist and self.track_artist.url)
                or self.album.album_artist.url)

    @property
    def sort_key(self):
        """A key that can be used to sort Albums into a reasonable order."""
        return (self.album.sort_key, self.track_num)

    _KEY_PREFIX = u"djdb/t:"

    @classmethod
    def get_key_name(cls, ufid):
        """Returns the datastore key name based on the track's UFID."""
        return cls._KEY_PREFIX + ufid

    def __init__(self, *args, **kwargs):
        """Constructor.

        If necessary, automatically sets the entity's key according
        to our standard scheme.
        """
        if 'ufid' in kwargs:
            assert 'key_name' not in kwargs
            kwargs['key_name'] = self.get_key_name(kwargs['ufid'])
        db.Model.__init__(self, *args, **kwargs)

    @property
    def ufid(self):
        """Returns the library UFID of the track's MP3."""
        return self.key().name()[len(self._KEY_PREFIX):]

    def __unicode__(self):
        return self.title

    @property
    def sorted_current_tags(self):
        """Returns a sorted list of tags."""
        return sorted(self.current_tags, key=unicode.lower)

    def has_tag(self, tag):
        """Returns true if tag 'tag' is currently set."""
        tag = tag.lower()
        return any(tag == t.lower() for t in self.current_tags)

    @property
    def is_explicit(self):
        """Returns True if the [Explicit] tag is set on this track."""
        return self.has_tag(EXPLICIT_TAG)

    @property
    def is_recommended(self):
        """Returns True if the [Recommended] tag is set on this track."""
        return self.has_tag(RECOMMENDED_TAG)


############################################################################


class SearchMatches(db.Model):
    """A set of objects matching a given search term.  We
    implement search by running datastore queries across these
    objects.
    """
    # What generation is this data a part of?  In the future we can use
    # this for development, schema changes, reindexing, etc.
    generation = db.IntegerProperty(required=True)

    # The name of the entity type.  In practice, the string returned by
    # my_obj.key().kind().
    entity_kind = db.StringProperty(required=True)

    # A field identifier, indicating where within the entity this
    # search term appeared.
    field = db.StringProperty(required=True)

    # A normalized search term.
    term = db.StringProperty(required=True)

    # When this collection of matches was created.
    timestamp = db.DateTimeProperty(auto_now=True)

    # A list of datastore keys for entities whose text metadata contains
    # the term "term".
    matches = db.ListProperty(db.Key)


############################################################################


class Document(db.Model):
    """A document is a piece of (possibly long) user generated text
    that is attached to a specific djdb object.
    """
    # The object that this document's text is the subject of.
    subject = db.ReferenceProperty(required=True)

    # The user who wrote the text.
    author = db.ReferenceProperty(User, required=True)

    # When this document was created.
    timestamp = db.DateTimeProperty(required=True, auto_now=True)

    @property
    def timestamp_display(self):
        """This is the time to show to users."""
        return time_util.convert_utc_to_chicago(self.timestamp)

    # What type of document this is.
    # Example: "review" for an Album review.
    doctype = db.CategoryProperty(required=True)

    # If True, this document should not be shown under normal
    # circumstances.
    is_hidden = db.BooleanProperty(required=True, default=False)

    # The title of this document.
    title = db.StringProperty()
    
    # The text of the document, exactly as it was entered by the user.
    # This might not be HTML-safe!
    unsafe_text = db.TextProperty()

    @property
    def text(self):
        """Returns a sanitized version of the text the user input."""
        return sanitize_html.sanitize_html(self.unsafe_text)

    @property
    def sort_key(self):
        # We want to sort documents in reverse chronological order.
        return tuple(-x for x in self.timestamp.utctimetuple())


############################################################################


class TagEdit(db.Model):
    """A user edit to an object's tags.

    The state of an object's tags is computed by merging together
    the various TagEdits.
    """
    # The object being tagged.
    subject = db.ReferenceProperty(required=True)

    # The user who made this edit.
    author = db.ReferenceProperty(User, required=True)

    # When this document was created.
    timestamp = db.DateTimeProperty(required=True, auto_now=True)

    # A list of the tags that were added.
    added = db.StringListProperty()

    # A list of the tags that were removed.
    removed = db.StringListProperty()

    @classmethod
    def fetch_and_merge(cls, obj):
        """Walk over an object's tag edit history and compute the
        current state of its tags.

        Args:
          obj: The object in question.  If obj has an 'import_tags'
            property, they are used to seed the set of tags.
        """
        current_tags = set(getattr(obj, "import_tags", []))
        edit_query = cls.all()
        edit_query.filter("subject =", obj)
        edit_query.order("timestamp")
        # TODO(trow): We should angrily complain if the number of tag
        # edits is too high.
        for edit in AutoRetry(edit_query).fetch(999):
            current_tags.difference_update(edit.removed)
            current_tags.update(edit.added)
        obj.current_tags = list(current_tags)
        obj.save()
        return current_tags

class Crate(db.Model):
    """Mode for a crate, which contains artists, albums, or tracks.
    """
    # The user who owns the crate item.
    user = db.ReferenceProperty(User, required=True)

    # List of keys to items.
    items = db.ListProperty(db.Key)
    
    # List of positions for ordering.
    # When the crate page is shown and reorders take place, you can't reorder the list directly each
    # time since the original positions are referenced in the list item id's, which do not change.
    # So you have to keep track of the order separately. When the crate page is reloaded, then the
    # actual item list should be reordered.
    # I suppose some javascript could be added to update the list item id's when reordering
    # takes place...
    order = db.ListProperty(int)
    
class CrateItem(db.Model):
    """Model for crate items that represent artists/albums/tracks entered by hand.
    """
    artist = db.StringProperty()
    album = db.StringProperty()
    track = db.StringProperty()
    label = db.StringProperty()
    notes = db.StringProperty()

#    @classmethod
