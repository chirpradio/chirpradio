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

from datetime import datetime, timedelta

from django import forms
from djdb import models
from common.autoretry import AutoRetry


def new(album, user):
    """Returns a new partially-initialized Document object for a comment.

    The new Document is in the same entity group as the album for which a
    comment is being written.

    Args:
      album: The album being commented on.
      user: The user writing the comment.
    """
    return models.Document(parent=album,
                           subject=album, author=user,
                           doctype=models.DOCTYPE_COMMENT)


class Form(forms.Form):
    text = forms.CharField(required=True, widget=forms.Textarea,
                           min_length=10, max_length=20000)


def fetch_recent(max_num_returned=10, days=None, start_dt=None):
    """Returns the most recent comments, in reverse chronological order."""
    if days is not None:
        if start_dt:
            end_dt = start_dt + timedelta(days=days)
        else:
            end_dt = datetime.now() + timedelta(days=days)
    else:
        end_dt = None

    com_query = models.Document.all()
    com_query.filter("doctype =", models.DOCTYPE_COMMENT)
    com_query.order("-created")
    if start_dt:
        com_query.filter("created >=", start_dt)
    if end_dt:
        com_query.filter("created <", end_dt)
    return AutoRetry(com_query).fetch(max_num_returned)

def get_or_404(doc_key):
    doc = models.Document.get(doc_key)
    if doc is None :
        return http.HttpResponse(status=404)
    return doc
