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

"""Forms for DJ Database."""

from datetime import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _
from djdb import models
from common.autoretry import AutoRetry
from google.appengine.ext import db

ALBUM_CATEGORY_CHOICES = [["", ""]]
ALBUM_CATEGORY_CHOICES += zip(models.ALBUM_CATEGORIES,
                              [category.replace('_', ' ').capitalize() for category in models.ALBUM_CATEGORIES])
PAGE_SIZE_CHOICES = [[10, 10],
                     [25, 25],
                     [50, 50],
                     [100, 100]]
ORDER_CHOICES = [['created', 'created'],
                 ['author', 'author']]
BROWSE_ORDER_CHOICES = [['created', 'created'],
                 ['author', 'author']]
months =['January', 'February', 'March', 'April', 'May', 'June', 'July',
         'August', 'September', 'October', 'November', 'December']
MONTH_CHOICES = zip(range(1, 13), months)
days = range(1, 32)
DAY_CHOICES = zip(days, days)
years = range(2009, datetime.now().year + 1)
YEAR_CHOICES = zip(years, years)

SORT_BY_CHOICES = [['', '-'],
                   ['artist', 'artist'],
                   ['album', 'album'],
                   ['track', 'track'],
                   ['duration', 'duration']]

class PartialAlbumForm(forms.Form):
    pronunciation = forms.CharField(required=False,
                                    widget=forms.TextInput(attrs={'size': 40}))
    label = forms.CharField(required=False,
                            widget=forms.TextInput(attrs={'size': 40}))
    year = forms.IntegerField(required=False,
                              widget=forms.TextInput(attrs={'size': 4, 'maxlength': 4}))
    is_compilation = forms.BooleanField(required=False, label='Is a compilation:')
    is_heavy_rotation = forms.BooleanField(required=False,
                                           label=_("Heavy rotation"))
    is_light_rotation = forms.BooleanField(required=False,
                                           label=_("Light rotation"))
    is_local_classic = forms.BooleanField(required=False,
                                          label=_("Local classic"))
    is_local_current = forms.BooleanField(required=False,
                                          label=_("Local current"))

class PartialArtistForm(forms.Form):
    pronunciation = forms.CharField(required=False,
                                    widget=forms.TextInput(attrs={'size': 40}))

class ListReviewsForm(forms.Form):
    author = forms.CharField(required=False)
    author_key = forms.CharField(required=False, widget=forms.HiddenInput)
#    category = forms.ChoiceField(required=False, choices=ALBUM_CATEGORY_CHOICES)
    page_size = forms.ChoiceField(required=False, choices=PAGE_SIZE_CHOICES)
    order = forms.ChoiceField(required=False, choices=ORDER_CHOICES)

class TagForm(forms.Form):
    name = forms.CharField(required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)

class ListTracksPlayedForm(forms.Form):
    from_month = forms.ChoiceField(required=False, choices=MONTH_CHOICES)
    from_day = forms.ChoiceField(required=False, choices=DAY_CHOICES)
    from_year = forms.ChoiceField(required=False, choices=YEAR_CHOICES)
    page_size = forms.ChoiceField(required=False, choices=PAGE_SIZE_CHOICES)

class ListActivityForm(forms.Form):
    from_month = forms.ChoiceField(required=False, choices=MONTH_CHOICES)
    from_day = forms.ChoiceField(required=False, choices=DAY_CHOICES)
    from_year = forms.ChoiceField(required=False, choices=YEAR_CHOICES)

class CrateForm(forms.Form):
    artist = forms.CharField(required=False,
                             label=_("Artist"))
    track = forms.CharField(required=False,
                            label=_("Song Title"))
    album = forms.CharField(required=False,
                            label=_("Album"))
    label = forms.CharField(required=False,
                            label=_("Label"))
    is_heavy_rotation = forms.BooleanField(required=False,
                                           label=_("Heavy rotation"))
    is_light_rotation = forms.BooleanField(required=False,
                                           label=_("Light rotation"))
    is_local_classic = forms.BooleanField(required=False,
                                          label=_("Local classic"))
    is_local_current = forms.BooleanField(required=False,
                                          label=_("Local current"))
    notes = forms.CharField(required=False,
                            label=_("Song Notes"),
                            widget=forms.Textarea(attrs={'class':'text'}))

class CrateItemsForm(forms.Form):
    crates = forms.ChoiceField(required=True, label=_("Select crate"))
    name = forms.CharField(required=False, label=_("Name"))
    is_default = forms.BooleanField(required=False, label=_("Default crate"))
    sort_by = forms.ChoiceField(required=False, choices=SORT_BY_CHOICES)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(CrateItemsForm, self).__init__(*args, **kwargs)

        crates_field = []
        crates = AutoRetry(models.Crate.all().filter("user =", user)).fetch(999)
        for crate in crates:
            if crate.name is None or crate.name == '':
                name = "<No name>"
            else:
                name = crate.name
            if crate.is_default:
                name += " (default)"
            crates_field.append((crate.key(), name))
        self.fields['crates'].choices = crates_field

        if 'is_default' in args[0] and args[0]['is_default']:
            self.fields['is_default'].widget.attrs['disabled'] = True

class BrowseForm(forms.Form):
    page_size = forms.ChoiceField(required=False, choices=PAGE_SIZE_CHOICES)
    reviewed = forms.BooleanField(required=False)
#    order = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        entity_kind = kwargs.pop('entity_kind')
        super(BrowseForm, self).__init__(*args, **kwargs)

        choices = [('artist', 'artist')]
        if entity_kind == 'album' or entity_kind == 'track':
            choices.append(('album', 'album'))
        if entity_kind == 'track':
            choices.append(('track', 'track'))
#        self.fields['order'].choices = choices

