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

"""Views for the auth system."""

# Python imports
import base64
import datetime
import logging
import os
# Django imports
from django import http
from django.template import loader, Context, RequestContext
# App Engine imports
from google.appengine.api import mail
from google.appengine.api import users as google_users
# Application imports
import auth
from auth import roles
from auth.decorators import require_role, require_signed_in_user
from auth import forms as auth_forms
from auth.models import User

# Require this role in order to access any management tasks.
USER_MANAGEMENT_ROLE = roles.VOLUNTEER_COORDINATOR


###
### Log-in and log-out pages
###

def hello(request):
    """Implements our login page."""
    redirect = '/'
    tmpl = loader.get_template('auth/hello.html')
    if request.method == 'GET':
        redirect = request.GET.get('redirect', '/')
        # Already signed in?  Then redirect immediately.
        if request.user:
            return http.HttpResponseRedirect(redirect)
        form = auth_forms.LoginForm(initial={
                'redirect': redirect,
                })
    else:
        form = auth_forms.LoginForm(request.POST)
        if form.is_valid():
            response = http.HttpResponseRedirect(form.cleaned_data['redirect'])
            auth.attach_credentials(response, form.user)
            # Update the last login time in the User record.
            form.user.last_login = datetime.datetime.now()
            form.user.save()
            return response
            
    ctx = RequestContext(request, {'form': form})
    return http.HttpResponse(tmpl.render(ctx))


def goodbye(request):
    """Implements our logout page."""
    # This makes our middleware handle the logout for us.
    response = http.HttpResponse('Dummy')
    response._logout = True
    return response


###
### A page to let users change their password
###

@require_signed_in_user
def change_password(request):
    """Change password page."""
    tmpl = loader.get_template('auth/change_password.html')
    ctx_vars = {
        'title': 'Change Password',
        }
    if request.method == 'GET':
        ctx_vars['form'] = auth_forms.ChangePasswordForm()
    else:
        form = auth_forms.ChangePasswordForm(request.POST)
        form.set_user(request.user)
        if not form.is_valid():
            ctx_vars['form'] = form
        else:
            request.user.set_password(form.cleaned_data['new_password'])
            request.user.save()
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(tmpl.render(ctx))


###
### Pages to allow a user to reset a forgotten password.
###

def forgot_password(request):
    """Request a a password reset email.

    A user can enter an email address into a form.  Submitting causes
    an email containing a URL that can be clicked to restore access.
    """
    if request.user:
        return http.HttpResponseForbidden('Logged-in users prohibited.')
    # TODO(trow): Rate-limit password reset emails?
    tmpl = loader.get_template('auth/forgot_password.html')
    ctx_vars = {
        'title': 'Recover Forgotten Password',
        }
    if request.method == 'GET':
        ctx_vars['form'] = auth_forms.ForgotPasswordForm()
    else:
        form = auth_forms.ForgotPasswordForm(request.POST)
        if not form.is_valid():
            ctx_vars['form'] = form
        else:
            email = ctx_vars['email'] = form.user.email
            # Assemble the URL that can be used to access the password
            # reset form.
            token = auth.get_password_reset_token(form.user)
            url = 'http://%s/auth/reset_password?token=%s' % (
                os.environ['HTTP_HOST'], token)
            # Construct and send the email message
            msg_tmpl = loader.get_template('auth/forgot_password_email.txt')
            msg_ctx = Context({'user': form.user, 'url': url})
            msg_body = msg_tmpl.render(msg_ctx)
            # Actually send the email message.
            # TODO(trow): This should come from a more general account.
            mail.send_mail(sender='trowbridge.jon@gmail.com',
                           to=form.user.email,
                           subject='Recovering your forgotten CHIRP password',
                           body=msg_body)
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(tmpl.render(ctx))


def reset_password(request):
    """Allow a user to reset their password.

    The user authenticates by presenting a security token.  Users will
    arrive at this page by clicking on the URL in the email they are
    sent by the /auth/forgot_password page.
    """
    if request.user:
        return http.HttpResponseForbidden('Logged-in users prohibited.')
    tmpl = loader.get_template('auth/reset_password.html')
    ctx_vars = {
        'Title': 'Reset Password',
        }
    user = None
    if request.method == 'GET':
        token = request.GET.get('token')
        if token is None:
            return http.HttpResponseForbidden('Missing token')
        email = auth.parse_passord_reset_token(token)
        if email is None:
            return http.HttpResponseForbidden('Invalid token')
        ctx_vars['form'] = auth_forms.ResetPasswordForm(
            initial={'token': token})
    else:
        form = auth_forms.ResetPasswordForm(request.POST)
        if not form.is_valid():
            ctx_vars['form'] = form
        else:
            token = form.cleaned_data['token']
            email = token and auth.parse_passord_reset_token(token)
            if email is None:
                return http.HttpResponseForbidden('Invalid token')
            user = User.get_by_email(email)
            if user is None:
                return http.HttpResponseForbidden('No user for token')
            user.set_password(form.cleaned_data['new_password'])
            # We are also logging the user in automatically, so record
            # the time.
            user.last_login = datetime.datetime.now()
            user.save()
            # Attach the user to the request so that our page will
            # display the chrome shown to logged-in users.
            request.user = user
    ctx = RequestContext(request, ctx_vars)
    response = http.HttpResponse(tmpl.render(ctx))
    if request.user:
        auth.attach_credentials(response, request.user)
    return response


###
### Simple user management tools.
###

@require_role(USER_MANAGEMENT_ROLE)
def main_page(request):
    """Lists all users."""
    tmpl = loader.get_template('auth/main_page.html')
    all_users = list(User.all().order('last_name').order('first_name'))
    num_active_users = sum(u.is_active for u in all_users)
    active = [u for u in all_users if u.is_active]
    inactive = [u for u in all_users if not u.is_active]
    ctx = RequestContext(request, {
            'title': 'User Management',
            'all_users': active + inactive,
            'num_active_users': num_active_users,
            })
    return http.HttpResponse(tmpl.render(ctx))


@require_role(USER_MANAGEMENT_ROLE)
def edit_user(request):
    tmpl = loader.get_template('auth/user_form.html')
    if request.method == 'GET':
        email = request.GET.get('email')
        user_to_edit = User.get_by_email(email)
        user_form = auth_forms.UserForm.from_user(user_to_edit)
    elif request.method == 'POST':
        user_form = auth_forms.UserForm(request.POST)
        if user_form.is_valid():
            user_to_edit = user_form.to_user()
            user_to_edit.save()
            # When finished, redirect user back to the user list.
            return http.HttpResponseRedirect('/auth/')
    ctx = RequestContext(request, {
            'title': 'Edit User',
            'user_to_edit': user_to_edit,
            'form': user_form,
            })
    return http.HttpResponse(tmpl.render(ctx))


@require_role(USER_MANAGEMENT_ROLE)
def add_user(request):
    tmpl = loader.get_template('auth/user_form.html')
    ctx_vars = {
        'title': 'Add New User',
        }
    if request.method == 'GET':
        ctx_vars['form'] = auth_forms.UserForm()
    elif request.method == 'POST':
        form = auth_forms.UserForm(request.POST)
        if not form.is_valid():
            ctx_vars['form'] = form
        if form.is_valid():
            user = form.to_user()
            user.save()
            ctx_vars['message'] = 'Successfully added user %s' % user.email
            ctx_vars['form'] = auth_forms.UserForm()
    ctx = RequestContext(request, ctx_vars)
    return http.HttpResponse(tmpl.render(ctx))


###
### A backdoor for sysadmins.  Useful during testing.  Probably should be
### turned off in production.
###

def bootstrap(request):
    """If the visitor is a chirpradio admin, create a user for them."""
    if request.user is None:
        g_user = google_users.get_current_user()
        if g_user is None:
            return http.HttpResponseRedirect(
                google_users.create_login_url(request.path))
        if not google_users.is_current_user_admin():
            return http.HttpResponseForbidden('Not a chirpradio project admin')
        user = User.get_by_email(g_user.email())
        if user:
            return http.HttpResponseForbidden(
                'User %s already exists' % user.email)
        user = User(email=g_user.email(), is_superuser=True)
        user.set_password("test")
        user.save()
        return http.HttpResponseRedirect(auth.create_login_url('/'))
    return http.HttpResponseForbidden("Already logged in")
