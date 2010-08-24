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

from django import forms
from django.forms import HiddenInput, PasswordInput
from auth.models import User
from auth.models import roles


class LoginForm(forms.Form):
    redirect = forms.CharField(widget=HiddenInput, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(required=True, widget=PasswordInput)
    
    def clean_email(self):
        self.cleaned_data['email'] = self.cleaned_data['email'].lower()
        self.user = User.get_by_email(self.cleaned_data['email'])
        if self.user is None:
            raise forms.ValidationError('Unknown email address')
        if not self.user.is_active:
            raise forms.ValidationError('Account not active')
        return self.cleaned_data['email']

    def clean_password(self):
        if 'email' in self.cleaned_data:
            self.user = User.get_by_email(self.cleaned_data['email'])
            if not self.user.password:
                raise forms.ValidationError('Password not set')
            if not self.user.check_password(self.cleaned_data['password']):
                raise forms.ValidationError('Incorrect password')
        return self.cleaned_data['password']


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(required=True, widget=PasswordInput)
    new_password = forms.CharField(required=True, widget=PasswordInput)
    confirm_new_password = forms.CharField(required=True, widget=PasswordInput)

    def set_user(self, user):
        self._user = user

    def clean_current_password(self):
        pw = self.cleaned_data['current_password']
        if not self._user.check_password(pw):
            raise forms.ValidationError('Incorrect password')
        return pw

    def clean_confirm_new_password(self):
        pw = self.cleaned_data['confirm_new_password']
        if pw != self.cleaned_data['new_password']:
            raise forms.ValidationError('Passwords are not the same')
        return pw


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(required=True)
    user = None

    def clean_email(self):
        self.cleaned_data['email'] = self.cleaned_data['email'].lower()
        self.user = User.get_by_email(self.cleaned_data['email'])
        if self.user is None:
            raise forms.ValidationError('Unknown email address')
        return self.cleaned_data['email']


class ResetPasswordForm(forms.Form):
    token = forms.CharField(required=True, widget=HiddenInput)
    new_password = forms.CharField(required=True, widget=PasswordInput)
    confirm_new_password = forms.CharField(required=True, widget=PasswordInput)

    def clean_confirm_new_password(self):
        pw = self.cleaned_data['confirm_new_password']
        if pw != self.cleaned_data['new_password']:
            raise forms.ValidationError('Passwords are not the same')
        return pw


class UserForm(forms.Form):
    original_email = forms.EmailField(widget=HiddenInput, required=False)
    email = forms.EmailField()
    first_name = forms.CharField()
    last_name = forms.CharField()
    dj_name = forms.CharField()
    password = forms.CharField(required=False)
    is_active = forms.BooleanField(initial=True, required=False)
    # We also plug in synthetic fields for all of our various roles.

    def clean_email(self):
        email = self.cleaned_data['email']
        if (email != self.cleaned_data.get('original_email')
            and User.get_by_email(email) is not None):
            raise forms.ValidationError('Email address already in use')
        return email.lower()

    def clean_first_name(self):
        # Remove leading and trailing whitespace.
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        # Remove leading and trailing whitespace.
        return self.cleaned_data['last_name'].strip()

    def clean_dj_name(self):
        # Remove leading and trailing whitespace.
        return self.cleaned_data['dj_name'].strip()
        
    @classmethod
    def from_user(cls, user):
        initial = {
            'original_email': user.email,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'dj_name': user.dj_name,
            'is_active': user.is_active,
            }
        for r in user.roles:
            initial['is_' + r] = True
        return cls(initial=initial)

    def to_user(self):
        data = self.cleaned_data.copy()

        user_roles = []
        for r in roles.ALL_ROLES:
            key = 'is_' + r
            if key in data:
                if data[key]:
                    user_roles.append(r)
                del data[key]
        data['roles'] = user_roles
            
        if data['original_email']:
            # update the user (edit form)...
            user = User.get_by_email(data['original_email'])
            for key, val in data.items():
                # update all attributes with form values except our 
                # placeholder field, original_email; also handle password as a special case
                if key == 'password':
                    if val:
                        # only change the password if it was filled in on the edit form:
                        user.set_password(val)
                elif key != 'original_email':
                    setattr(user, key, val)
            user.save()
        else:
            # creating new user...
            del data['original_email']
            initial_password = None
            if data['password']:
                # this is uncommon
                initial_password = data['password']
            del data['password']
            user = User(**data)
            if initial_password:
                user.set_password(initial_password)
                user.save()
        return user


# Plug in form fields for all of our roles.
for r in roles.ALL_ROLES:
    UserForm.base_fields['is_' + r] = forms.BooleanField(initial=False,
                                                         required=False)
