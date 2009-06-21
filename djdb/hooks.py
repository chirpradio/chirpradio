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

"""Web hooks (i.e. things executed by task queues) for the DJ Database."""

from django import http
from google.appengine.api import users
from djdb import search


def optimize_index(request):
    if not users.is_current_user_admin():
        return http.HttpResponse("no", status=403)
    if request.method == "POST":
        term = request.POST.get("term")
    elif request.method == "GET":
        term = request.GET.get("term")
    else:
        return http.HttpResponse("no", status=403)
    if term:
        search.optimize_index(term)
    return http.HttpResponse("ok")
    
    
