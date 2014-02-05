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

import random
import datetime
import logging

from google.appengine.ext import db, search
from django.core.urlresolvers import reverse

from auth.models import User
from traffic_log import constants
from common.autoretry import AutoRetry
from common import time_util

log = logging.getLogger()

class SpotAtConstraint(object):
    """A spot within its constraint."""
    
    def __init__(self, spot_constraint, spot):
        self.spot = spot
        
        q = (TrafficLogEntry.all()
                .filter("log_date =", time_util.chicago_now().date())
                .filter("spot =", spot)
                .filter("hour =", spot_constraint.hour)
                .filter("slot =", spot_constraint.slot)
                .filter("dow =", spot_constraint.dow))
        if AutoRetry(q).count(1):
            self.finished = True
        else:
            self.finished = False

class SpotConstraint(db.Model):
    dow      = db.IntegerProperty(verbose_name="Day of Week", choices=constants.DOW)
    hour     = db.IntegerProperty(verbose_name="Hour", choices=constants.HOUR)
    slot     = db.IntegerProperty(verbose_name="Spot", choices=constants.SLOT)
    spots    = db.ListProperty(db.Key)
    
    def iter_spots(self):
        for spot in AutoRetry(Spot).get(self.spots):
            if spot is None:
                # there was a bug where deleted spots had lingering constraints.
                # See http://code.google.com/p/chirpradio/issues/detail?id=103
                continue
            copy, is_logged = spot.get_spot_copy(self.dow, self.hour, self.slot)
            if copy is None:
                # probably a spot with expired copy (or copy not yet created)
                continue
            yield spot
    
    def iter_spots_at_constraint(self):
        for spot in self.iter_spots():
            yield SpotAtConstraint(self, spot)
    
    def as_query_string(self):
        return "hour=%d&dow=%d&slot=%d" % (self.hour, self.dow, self.slot)
    
    def url_to_finish_spot(self, spot):
        url = ""
        if len(spot.random_spot_copies) > 0:
            url = reverse('traffic_log.finishReadingSpotCopy', args=(spot.random_spot_copies[0],))
            url = "%s?%s" % (url, self.as_query_string())
        return url
    
    @property
    def readable_slot_time(self):
        min_slot = str(self.slot)
        if min_slot == '0':
            min_slot = '00'
        meridian = 'am'
        hour = self.hour
        if hour > 12:
            meridian = 'pm'
            hour = hour - 12
        # exceptions:
        if hour == 12:
            meridian = 'pm'
        if hour == 0:
            hour = 12
        return "%s:%s%s" % (hour, min_slot, meridian)

    def __init__(self, *args, **kw):
        key_name = "%d:%d:%d" % (kw['dow'], kw['hour'], kw['slot']) 
        super(SpotConstraint, self).__init__(*args, **kw)


class Spot(db.Model):
    """
    """
    active    = db.BooleanProperty(default=True)
    title     = db.StringProperty(verbose_name="Spot Title", required=True)
    type      = db.StringProperty(verbose_name="Spot Type", required=True, choices=constants.SPOT_TYPE)
    created   = db.DateTimeProperty(auto_now_add=True)
    updated   = db.DateTimeProperty(auto_now=True)
    random_spot_copies = db.ListProperty(db.Key)

    def all_spot_copy(self):
        # two queries (since there is no OR statement).  
        # One for copy that does not expire and one for not-yet-expired copy
        q = SpotCopy.all().filter("spot =", self).filter("expire_on =", None)
        active_spots = [c for c in AutoRetry(q)]
        q = SpotCopy.all().filter("spot =", self).filter("expire_on >", datetime.datetime.now())
        for c in AutoRetry(q):
            active_spots.append(c)
        return active_spots
    
    def current_spot_copy(self):
        # two queries (since there is no OR statement).  
        # One for copy that does not expire and one for not-yet-expired copy
        active_spots = []
        q = SpotCopy.all().filter("spot =", self).filter("expire_on =", None).filter("start_on <=", datetime.datetime.now())
        for c in AutoRetry(q):
            if c.has_started():
                active_spots.append(c)
        q = SpotCopy.all().filter("spot =", self).filter("expire_on >", datetime.datetime.now())
        for c in AutoRetry(q):
            if c.has_started():
                active_spots.append(c)
        return active_spots

    def add_spot_copy(self, spot_copy):
        self.random_spot_copies.append(spot_copy.key())
        AutoRetry(self).save()
    
    def _expunge_expired_spot_copies(self, random_spot_copies):
        """Check to see if any of the cached spot copies have expired.
        
        if so, expunge them and save the spot with a new list.
        """
        one_expired = False
        q = SpotCopy.all().filter("spot =", self)
        q = q.filter("__key__ in", random_spot_copies)
        
        expired_spot_copy_keys = []
        for copy in q:
            if copy.expire_on and copy.expire_on <= datetime.datetime.now():
                expired_spot_copy_keys.append(copy.key())
        
        for expired_key in expired_spot_copy_keys:
            for k in random_spot_copies:
                one_expired = True
                if str(k) == str(expired_key):
                    random_spot_copies.remove(k)
        if one_expired:
            # only save if we have to since expunging will be rare
            self.random_spot_copies = random_spot_copies
            AutoRetry(self).save()
            
    def _expunge_unstarted_spot_copies(self, random_spot_copies):
        one_unstarted = False
        q = SpotCopy.all().filter("spot =", self)
        q = q.filter("__key__ in", random_spot_copies)
        
        unstarted_spot_copy_keys = []
        for copy in q:
            if not copy.has_started():
                unstarted_spot_copy_keys.append(copy.key())
        
        for unstarted_key in unstarted_spot_copy_keys:
            for k in random_spot_copies:
                one_unstarted = True
                if str(k) == str(unstarted_key):
                    random_spot_copies.remove(k)
        if one_unstarted:
            # only save if we have to since expunging will be rare
            self.random_spot_copies = random_spot_copies
            AutoRetry(self).save()

    def shuffle_spot_copies(self, prev_spot_copy=None):
        """Shuffle list of spot copy keys associated with this spot."""
        spot_copies = [spot_copy.key() for spot_copy in self.current_spot_copy()]
        random.shuffle(spot_copies)

        # Get spot copies that have been read in the last period (two hours).
        date = datetime.datetime.now().date() - datetime.timedelta(hours=2)
        query = TrafficLogEntry.all().filter('log_date >=', date)
        recent_spot_copies = []
        for entry in query:
            recent_spot_copies.append(entry.spot_copy.key())
		
        # Iterate through list, moving spot copies that have been read in the past period to the
        # end of the list.
        for i in range(len(spot_copies)):
            if spot_copies[0] in recent_spot_copies:
                spot_copies.append(spot_copies.pop(0))
        
        # If all spot copies were read in the last period, the first item in the new shuffled list
        # may by chance be the last one read. If so, move to the end.
        if prev_spot_copy and spot_copies[0] == prev_spot_copy:
            spot_copies.append(spot_copies.pop(0))
            
        self.random_spot_copies = spot_copies

    def get_spot_copy(self, dow, hour, slot):
        spot_copy = None
        is_logged = False
        
        # If random spot copy list for this spot is empty, fill and shuffle.
        if len(self.random_spot_copies) == 0:
            self.shuffle_spot_copies()
            AutoRetry(self).save()
        
        self._expunge_expired_spot_copies(self.random_spot_copies)
        self._expunge_unstarted_spot_copies(self.random_spot_copies)
        
        # if spot copies exist and none have expired...
        if len(self.random_spot_copies) > 0:
            # Return the spot copy that a DJ just read (even though the 
            # finish link will be disabled)
            # or return the next random one for reading

            today = time_util.chicago_now().date()
            q = (TrafficLogEntry.all()
                    .filter("log_date =", today)
                    .filter("spot =", self)
                    .filter("dow =", dow)
                    .filter("hour =", hour)
                    .filter("slot =", slot))
                
            # Spot copy exists for dow, hour, and slot. Return it.
            if AutoRetry(q).count(1):
                existing_logged_spot = AutoRetry(q).fetch(1)[0]
                spot_copy = existing_logged_spot.spot_copy
                is_logged = True
            
            # Return next random spot copy.
            else:
                spot_copy = AutoRetry(db).get(self.random_spot_copies[0])
        
        return spot_copy, is_logged

    def finish_spot_copy(self):
        # Pop off spot copy from this spot's shuffled list of spot copies.
        spot_copy = self.random_spot_copies.pop(0)
        
        # If shuffled spot copy list is empty, regenerate.
        if len(self.random_spot_copies) == 0:
            self.shuffle_spot_copies(spot_copy)
            
        AutoRetry(self).save()

    @property
    def constraints(self):
        return SpotConstraint.gql("where spots =:1 order by dow, hour, slot", self.key())

    def get_add_copy_url(self):
        return reverse('traffic_log.views.addCopyForSpot', args=(self.key(),))

    def get_absolute_url(self):
        return '/traffic_log/spot/%s/' % self.key()

class SpotCopy(db.Model):
    
    spot        = db.ReferenceProperty(Spot)
    underwriter = db.TextProperty(required=False)
    body        = db.TextProperty(verbose_name="Spot Copy",  required=True)
    start_on   = db.DateTimeProperty(verbose_name="Start Date", required=False, default=None)
    expire_on   = db.DateTimeProperty(verbose_name="Expire Date", required=False, default=None)
    author      = db.ReferenceProperty(User)
    created     = db.DateTimeProperty(auto_now_add=True)
    updated     = db.DateTimeProperty(auto_now=True)
    
    def __unicode__(self):
        body_words = self.body.split(" ")
        def shorten(words, maxlen=55):
            s = ' '.join(words)
            if len(s) > maxlen:
                words.pop()
                return shorten(words)
            else:
                return s
        shortened_body = shorten([w for w in body_words])
        return u"%s..." % shortened_body
    
    __str__ = __unicode__

    def get_absolute_url(self):
        return '/traffic_log/spot-copy/%s/' % self.key()

    def get_delete_url(self):
        return reverse('traffic_log.deleteSpotCopy', args=(self.key(),))

    def get_edit_url(self):
        return reverse('traffic_log.editSpotCopy', args=(self.key(),))
    
    def has_started(self):
        if self.start_on == None or self.start_on <= datetime.datetime.now():
            return True
        else:
            return False

## there can only be one entry per date, hour, slot
class TrafficLogEntry(db.Model):
    log_date  = db.DateProperty()
    spot      = db.ReferenceProperty(Spot)
    spot_copy = db.ReferenceProperty(SpotCopy)
    dow       = db.IntegerProperty()
    hour      = db.IntegerProperty()
    slot      = db.IntegerProperty()
    scheduled = db.ReferenceProperty(SpotConstraint)
    readtime  = db.DateTimeProperty()
    reader    = db.ReferenceProperty(User)
    created   = db.DateTimeProperty(auto_now_add=True)

    
