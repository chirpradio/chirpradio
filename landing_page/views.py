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

"""Views for the site landing page."""

from django import http
from django.template import RequestContext, loader


def landing_page(request):
    template = loader.get_template('landing_page/landing_page.html')
    ctx = RequestContext(request, {
            'title': 'Welcome to chirpradio',
            })
    return http.HttpResponse(template.render(ctx))


def four_oh_four(request):
    return http.HttpResponse("No such page: " + request.path,
                             mimetype="text/plain",
                             status=404)

def error_on_purpose(request):
    raise RuntimeError(
            "When the moon shines on the 5th house on the 7th hour, "
            "your shoe laces will unravel.")