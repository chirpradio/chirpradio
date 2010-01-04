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

import traceback
from django.utils import simplejson
from django.http import HttpResponse
import logging

log = logging.getLogger()

def as_json(handler):
    def makejson(*args, **kwargs):
        try:
            r = handler(*args, **kwargs)
            status = 200
        except Exception, err:
            log.exception("in JSON response")
            r = {
                'success':False,
                'error': repr(err),
                'traceback': traceback.format_exc()
            }
            status = 500
        return HttpResponse(simplejson.dumps(r), 
                            mimetype='application/json', 
                            status=status )
    return makejson