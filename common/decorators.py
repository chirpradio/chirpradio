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
import traceback

from django.utils import simplejson
from django.http import HttpResponse


def respond_with_json(func):
    """Convert a handler's return value into a JSON-ified HttpResponse."""
    def wrapper(*args, **kwargs):
        try:
            response_py = func(*args, **kwargs)
            status = 200
        except Exception, err:
            # @TODO(kumar) really REALLY need to hook into Django's email mailer here
            logging.exception('Error in JSON response')
            response_py = {
                'success': False,
                'error': repr(err),
                'traceback': traceback.format_exc()
                }
            status = 500
        return HttpResponse(simplejson.dumps(response_py), 
                            mimetype='application/json', 
                            status=status )
    return wrapper
