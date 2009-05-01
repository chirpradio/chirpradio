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

"""Authentication model for CHIRP applications."""

import hashlib
import time
from google.appengine.ext import db
from auth import roles


class User(db.Model):
    """CHIRP radio's canonical user class.

    This object is designed to be contrib.auth-like but not
    necessarily compatible.  We only keep basic information about the
    user here; essentially only things we need for "sysadmin-y" tasks.
    More detailed information should go in the volunteer tracker or
    other 
    """
    email = db.EmailProperty(required=True)
    first_name = db.StringProperty()
    last_name = db.StringProperty()

    # This is the SHA1 hash of the user's password.
    password = db.StringProperty()
    # We omit Django's is_staff property.
    is_active = db.BooleanProperty(default=True, required=True)
    # Superusers are given unfettered access to the site, and are
    # considered to be in every role.
    is_superuser = db.BooleanProperty(default=False, required=True)
    last_login = db.DateTimeProperty(auto_now_add=True, required=True)
    date_joined = db.DateTimeProperty(auto_now_add=True, required=True)

    # We omit Django's groups property, and replace it with 'roles'.
    # A role is just a constant string identifier.  For a list of
    # the possible roles, see the auth.roles module.
    #
    # Properties for checking if a user has a particular role are
    # automatically patched into the User class.  The following two
    # expressions are equivalent:
    #   roles.ROLE_NAME in user.roles
    #   user.is_role_name
    # 
    # TODO(trow): Add validation that all roles are valid.
    roles = db.StringListProperty()


    def __unicode__(self):
        name_parts = []
        if self.first_name:
            name_parts.append(self.first_name)
        if self.last_name:
            name_parts.append(self.last_name)
        if not name_parts:
            name_parts.append(self.email)
        return u' '.join(name_parts)

    def __str__(self):
        return unicode(self).encode('utf-8')

    @classmethod
    def _hash_password(cls, plaintext):
        return hashlib.sha1(plaintext).hexdigest()

    def set_password(self, plaintext):
        """Store the SHA1 hash in the password property."""
        salt = '%04x' % int(0xffff * (time.time() % 1))
        self.password = salt + User._hash_password(salt + plaintext)

    def check_password(self, plaintext):
        if not self.password or len(self.password) < 4:
            return False
        salt = self.password[:4]
        hashed = self.password[4:]
        return hashed == User._hash_password(salt + plaintext)

    @classmethod
    def get_by_email(cls, email):
        query = db.Query(cls)
        query.filter('email =', email)
        if query.count() == 0:
            return None
        elif query.count() == 1:
            return query.get()
        else:
            raise LookupError('User email collision for %s' % email)


# Patch the User class to provide properties for checking roles.
# These are useful in templates.
for role in roles.ALL_ROLES:
    property_name = 'is_' + role.lower()
    assert not hasattr(User, property_name)
    setattr(User, property_name,
            property(lambda self: self.is_superuser or role in self.roles))


        
