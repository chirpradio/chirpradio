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

from django.http import HttpResponse, HttpResponseRedirect
from google.appengine.api import taskqueue

from common.models import Config, load_dbconfig_into_memcache
from common.utilities import as_json

log = logging.getLogger()

def _init_config(request):
    q = Config.all()
    if q.count(1) == 0:
        c = Config()
        c.varname = "dummy"
        c.value = "you can safely delete this after creating new var/vals"
        c.put()
        return HttpResponse(
            """Config initialized. You can now add new values 
            in the <a href="/_ah/admin">Datastore admin</a>.""")
    else:
        return HttpResponse(
            """Config does not need initialization. You can
            edit the config in the <a href="/_ah/admin">Datastore admin</a>.""")

@as_json
def _make_json_error(request):
    """view for the tests that purposefully raises an exception while decorated as a JSON handler.
    """
    # TODO(kumar) set this up programmatically in the tests instead?
    raise RuntimeError(
            "When the moon shines on the 5th house on the 7th hour, "
            "your shoe laces will unravel.")


def appengine_warmup(request):
    """Called periodically on new app engine instances.

    See Warming Requests in
    http://code.google.com/appengine/docs/python/config/appconfig.html

    """
    log.info("Warming up")
    taskqueue.add(url='/api/current_playlist', method='GET')
    load_dbconfig_into_memcache()
    # Import jobs to register them.
    # TODO(Kumar) figure out a better way to register job workers
    from playlists import reports
    from traffic_log import views
    return HttpResponse("it's getting hot in here")
