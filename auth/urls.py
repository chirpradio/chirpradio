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

"""URLs for the auth system."""

from django.conf import settings
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    '',
    # Log in
    (r'^hello/?', 'auth.views.hello'),
    # Log out
    (r'^goodbye/?', 'auth.views.goodbye'),
    # Change your password
    (r'^change_password/?', 'auth.views.change_password'),
    # Send a password reset email.
    (r'^forgot_password/?', 'auth.views.forgot_password'),
    # Reset a forgotten password.
    (r'^reset_password/?', 'auth.views.reset_password'),
    # Main user management page.
    url(r'^/?$', 'auth.views.main_page', name='auth.landing_page'),
    # Edit a user.
    (r'^edit_user/?', 'auth.views.edit_user'),
    # Add a user.
    (r'^add_user/?', 'auth.views.add_user'),

    # User search for jquery.autocomplete
    (r'index_users', 'auth.views.index_users'),
    (r'search\.txt', 'auth.views.user_search_for_autocomplete'),
    
    (r'^token', 'auth.views.token'),

    # Bootstrap a test account from a Google account.
    (r'^_bootstrap/?', 'auth.views.bootstrap'),
)
