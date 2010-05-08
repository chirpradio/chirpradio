#!/usr/bin/env python
#
# Google App Engine Internal Error Middleware
# Copyright (C) 2009 Wesley Tanaka <http://wtanaka.com>
#
# Portions of this code Copyright 2010 The Chicago Independent Radio Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

import django.http
import django.template.loader
import django.template

from google.appengine.api.datastore_errors import InternalError
from google.appengine.api.datastore_errors import Timeout
from google.appengine.api.datastore_errors import TransactionFailedError
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
import google.appengine.api.labs.taskqueue
import google.appengine.runtime

# each tuple item contains:
#   (exception type, readable exception name, status code for response)
CATCHABLE = (
    (Timeout, 'datastore_errors.Timeout', 503),
    (InternalError, 'datastore_errors.InternalError', 500),
    (google.appengine.api.labs.taskqueue.TransientError,
     'taskqueue.TransientError', 503),
    (CapabilityDisabledError, 'CapabilityDisabledError', 503),
    (google.appengine.runtime.DeadlineExceededError,
     'runtime.DeadlineExceededError', 503),
    (google.appengine.api.labs.taskqueue.InternalError,
     'taskqueue.InternalError', 500),
    (TransactionFailedError, 'TransactionFailedError', 503),
)

def expand_exception(exception):
    """Returns tuple of (exception class, readable exception name, 
    and status code for the response).
    """
    for e_type, readable_exception, status_code in CATCHABLE:
        if isinstance(exception, e_type):
            return e_type, readable_exception, status_code
    
    return exception.__class__, exception.__class__.__name__, 500

class GoogleAppEngineErrorMiddleware:
    """Display a default template on internal google app engine errors"""
    def process_exception(self, request, exception):
        logging.exception("Exception in request:")
        e_type, readable_exception, status_code = expand_exception(exception)
        
        t = django.template.loader.get_template('errors/exception-handler.html')
        html = t.render(django.template.Context({
                        'exception': exception, 
                        'readable_exception': readable_exception
                    }))
        
        response = django.http.HttpResponseServerError(html)
        response.status_code = status_code
        return response
