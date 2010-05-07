#!/usr/bin/env python
# vim:set ts=2 sw=2 et:
#
# Google App Engine Internal Error Middleware
# Copyright (C) 2009 Wesley Tanaka <http://wtanaka.com>
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

from google.appengine.api.datastore_errors import InternalError
from google.appengine.api.datastore_errors import Timeout
from google.appengine.api.datastore_errors import TransactionFailedError
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
import google.appengine.api.labs.taskqueue
import google.appengine.runtime

CATCHABLE = (
 (Timeout, 'timeout.html', 503),
 (InternalError, 'internal-error.html', 500),
 (google.appengine.api.labs.taskqueue.TransientError,
  'transient-error.html', 503),
 (CapabilityDisabledError, 'capability-disabled.html', 503),
 (google.appengine.runtime.DeadlineExceededError,
  'deadline-exceeded.html', 503),
 (google.appengine.api.labs.taskqueue.InternalError,
  'taskqueue-internal-error.html', 500),
 (TransactionFailedError, 'transaction-failed.html', 503),
)

def render(template, template_values):
  import django.template.loader
  t = django.template.loader.get_template(template)
  import django.template
  return t.render(django.template.Context(template_values))

class GoogleAppEngineErrorMiddleware:
  """Display a default template on internal google app engine errors"""
  def process_exception(self, request, exception):
    logging.exception("Exception in request:")
    for e_type, template_name, status in CATCHABLE:
      if isinstance(exception, e_type):
        logging.info("GoogleAppEngineErrorMiddleware is handling this")
        html = render(template_name, {'exception': exception})
        response = django.http.HttpResponseServerError(html)
        response.status_code = status
        return response
