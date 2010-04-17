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

"""URLs for the DJ Database."""

from django.conf import settings
from django.conf.urls.defaults import patterns
from djdb import models


# "/djdb/" has six characters, and needs to be stripped off when assembling
# our pattern.
IMAGE_URL_PATTERN = '^' + models.DjDbImage.URL_PREFIX[6:]


urlpatterns = patterns(
    '',
    # Landing page
    (r'^/?$', 'djdb.views.landing_page'),

    # Update albums from landing page
    (r'^update$', 'djdb.views.update_albums'),
    
    # Artist information page
    (r'artist/(.*)/info', 'djdb.views.artist_info_page'),

    # Update albums.
    (r'artist/.*/update', 'djdb.views.update_albums'),

    # Artist search for jquery.autocomplete
    (r'artist/search\.txt', 'djdb.views.artist_search_for_autocomplete'),
    
    # Album information page
    (r'album/(.*)/info', 'djdb.views.album_info_page'),

    # Update tracks.
    (r'album/(.*)/update', 'djdb.views.update_tracks'),

    # Album reviews.
    (r'album/(.*)/new_review', 'djdb.views.album_new_review'),
    (r'album/(.*)/edit_review/(.*)', 'djdb.views.album_edit_review'),
    
    # Album comments.
    (r'album/(.*)/new_comment', 'djdb.views.album_new_comment'),
    (r'album/(.*)/edit_comment/(.*)', 'djdb.views.album_edit_comment'),
    
    # Album search for jquery.autocomplete
    (r'album/search\.txt', 'djdb.views.album_search_for_autocomplete'),
    
    # Album category page.
    (r'category/(.*)', 'djdb.views.category_page'),
    
    # Track search for jquery.autocomplete
    (r'track/search\.txt', 'djdb.views.track_search_for_autocomplete'),
    
    # Crate page.
    (r'^crate/?$', 'djdb.views.crate_page'),
    # Add crate item.
    (r'crate/add_item', 'djdb.views.add_crate_item'),
    # Remove crate item.
    (r'crate/remove_item', 'djdb.views.remove_crate_item'),
    # Reorder crate items.
    (r'crate/reorder', 'djdb.views.reorder'),
    
    (r'update/artists/bulk_add', 'djdb.views.artists_bulk_add'),
    
    # Images
    (IMAGE_URL_PATTERN, 'djdb.views.image'),

    # Bootstrap -- development only!
    (r'_bootstrap', 'djdb.bootstrap.bootstrap'),

    # Web hook for index optimization
    (r'_hooks/optimize_index', 'djdb.hooks.optimize_index'),
)
