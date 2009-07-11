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

"""Utilities for working with dates and time."""

import datetime

def convert_utc_to_chicago(dt):
    if dt.tzinfo is None:
        # per app engine docs, all datetimes 
        # are set to UTC but in actuality this means 
        # their tzinfo properties are None
        dt = dt.replace(tzinfo=utc_tzinfo)
    return dt.astimezone(central_tzinfo)

# This code is mostly lifted from the docs:
# http://code.google.com/appengine
# /docs/python/datastore/typesandpropertyclasses.html#datetime

# TODO(kumar) Needs some unit tests

class Central_tzinfo(datetime.tzinfo):
    """Central timezone."""
    
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-6) + self.dst(dt)
    
    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))
    
    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))
        
        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        else:
            return datetime.timedelta(hours=0)
    
    def tzname(self, dt):
        if self.dst(dt) == datetime.timedelta(hours=0):
            return "CST"
        else:
            return "CDT"

central_tzinfo = Central_tzinfo()

class UTC_tzinfo(datetime.tzinfo):
    """Universal timezone (UTC)."""
    
    def utcoffset(self, dt):
        return datetime.timedelta(0)
    
    def tzname(self, dt):
        return "UTC"
    
    def dst(self, dt):
        return datetime.timedelta(0)

utc_tzinfo = UTC_tzinfo()


