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

"""Common data models shared across all apps."""

import logging

from google.appengine.api import memcache
from google.appengine.ext import db

from common.autoretry import AutoRetry

log = logging.getLogger()


def make_key(key):
    return 'dbconfig.%s' % key


class DBConfig(object):
    """A datastore config dictionary.

    Some configuration params cannot be hard coded into settings.py
    and must be stored in the App Engine datastore.  This object allows you
    to set and retrieve those settings.
    """

    def get(self, varname, default=None):
        try:
            return self[varname]
        except KeyError:
            return default

    def _memcache(self, key, val):
        key = make_key(key)
        try:
            memcache.set(key, val)
        except Exception, exc:
            log.error('Setting %s: %s' % (key, exc))

    def __getitem__(self, varname):
        try:
            cached = memcache.get(make_key(varname))
        except Exception, exc:
            log.error('Getting %s: %s' % (make_key(varname), exc))
            cached = False
        if cached:
            return cached

        q = Config.all().filter("varname =", varname)
        if AutoRetry(q).count(1) == 0:
            raise KeyError("No config value with varname %r" % varname)
        else:
            value = AutoRetry(q).fetch(1)[0].value
            self._memcache(varname, value)
            return value

    def __setitem__(self, varname, value):
        q = Config.all().filter("varname =", varname)
        if q.count(1) == 1:
            cfg = AutoRetry(q).fetch(1)[0]
        else:
            cfg = Config()

        cfg.varname = varname
        cfg.value = value
        AutoRetry(cfg).put()
        self._memcache(varname, value)


class Config(db.Model):
    varname = db.StringProperty()
    value = db.StringProperty()


def load_dbconfig_into_memcache():
    for c in Config.all():
        memcache.set(make_key(c.varname), c.value)
