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

from google.appengine.ext import db, search
from django.core.urlresolvers import reverse

from auth.models import User
from traffic_log import constants
from common.autoretry import AutoRetry


class SpotConstraint(search.SearchableModel):
    dow      = db.IntegerProperty(verbose_name="Day of Week", choices=constants.DOW)
    hour     = db.IntegerProperty(verbose_name="Hour", choices=constants.HOUR)
    slot     = db.IntegerProperty(verbose_name="Spot", choices=constants.SLOT)
    spots    = db.ListProperty(db.Key)
    
    def iter_spots(self):
        for spot in AutoRetry(Spot).get(self.spots):
            yield spot
    
    def as_query_string(self):
        return "hour=%d&dow=%d&slot=%d" % (self.hour, self.dow, self.slot)
    
    def url_to_finish_spot(self, spot):
        url = reverse('traffic_log.finishReadingSpotCopy', args=(spot.key(),))
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
        search.SearchableModel.__init__(self, *args, **kw)


class Spot(search.SearchableModel):
    """
    """
    title     = db.StringProperty(verbose_name="Spot Title", required=True)
    type      = db.StringProperty(verbose_name="Spot Type", required=True, choices=constants.SPOT_TYPE)
    created   = db.DateTimeProperty(auto_now_add=True)
    updated   = db.DateTimeProperty(auto_now=True)
    
    @property
    def copy_at_random(self):
        possible_copy = [
            c for c in AutoRetry(SpotCopy.all().filter("spot =", self))
        ]
        # TODO(kumar) filter out expired copy
        if len(possible_copy) == 0:
            raise ValueError("Spot %r of type %r does not have any copy associated with it" % (
                                                                            self.title, self.type))
        return random.choice(possible_copy)
    
    @property
    def constraints(self):
        return SpotConstraint.gql("where spots =:1 order by dow, hour, slot", self.key())

    def get_absolute_url(self):
        return '/traffic_log/spot/%s/' % self.key()

class SpotCopy(search.SearchableModel):
    
    spot        = db.ReferenceProperty(Spot)
    underwriter = db.TextProperty(required=False)
    body        = db.TextProperty(verbose_name="Spot Copy",  required=False)
    expire_on   = db.DateTimeProperty(verbose_name="Expire Date", required=False, default=None)
    author      = db.ReferenceProperty(User)
    created     = db.DateTimeProperty(auto_now_add=True)
    updated     = db.DateTimeProperty(auto_now=True)

    def get_absolute_url(self):
        return '/traffic_log/spot-copy/%s/' % self.key()

## there can only be one entry per date, hour, slot
class TrafficLogEntry(search.SearchableModel):
    log_date  = db.DateProperty()
    spot      = db.ReferenceProperty(Spot)
    spot_copy = db.ReferenceProperty(SpotCopy)
    hour      = db.IntegerProperty()
    slot      = db.IntegerProperty()
    scheduled = db.ReferenceProperty(SpotConstraint)
    readtime  = db.DateTimeProperty()
    reader    = db.ReferenceProperty(User)
    created   = db.DateTimeProperty(auto_now_add=True)

    
