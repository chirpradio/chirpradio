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
import functools
import traceback
import logging

from django.utils import simplejson
from django import http
from django.http import HttpResponse

from jobs import job_worker, job_product


log = logging.getLogger()


def as_json(handler):
    def makejson(*args, **kwargs):
        try:
            r = handler(*args, **kwargs)
            status = 200
        except Exception, err:
            # @TODO(kumar) really REALLY need to hook into
            # Django's email mailer here
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


def as_encoded_str(s, encoding='utf8', errors='strict'):
    """Ensures passed argument is always an encoded string if it's Unicode.

    However, if it's not string-like then it is returned as is.
    """
    if isinstance(s, unicode):
        s = s.encode(encoding, errors)
    return s


def http_send_csv_file(fname, fields, items):
    import csv

    # dump item using key fields
    def item2row(i):
        return [as_encoded_str(i[key], encoding='utf8') for key in fields]

    # use response obj to set filename of downloaded file
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = "attachment; filename=%s.csv" % (fname)

    # write data out
    out = csv.writer(response)
    out.writerow(fields)
    for item in items:
        out.writerow(item2row(item))
    #
    return response


def _access_restrictor(role):
    def restrict_access(request):
        if (role not in request.user.roles and
            not request.user.is_superuser):
            return http.HttpResponseForbidden(
                    'Page requires role "%s"' % role)
    return restrict_access


def restricted_job_worker(job_name, required_role):
    return job_worker(job_name,
                      pre_request=_access_restrictor(required_role))


def restricted_job_product(job_name, required_role):
    return job_product(job_name,
                       pre_request=_access_restrictor(required_role))


def cronjob(handler):
    """
    Wraps a view function that is a cron handler.

    If the request does not contain the magic cron header
    from Google App Engine, a 400 response is returned.
    See: https://developers.google.com/appengine/docs/python/config/cron
    """
    @functools.wraps(handler)
    def handle(request, *args, **kwargs):
        if not request.META.get('HTTP_X_APPENGINE_CRON') == 'true':
            log.error('Not a request from cron')
            return http.HttpResponseBadRequest()
        return handler(request, *args, **kwargs)
    return handle
