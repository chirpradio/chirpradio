import datetime
from google.appengine.ext import db
from google.appengine.tools import bulkloader
from google.appengine.api import datastore_types
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from auth import models

#    email:4,first_name:2,last_name:3,password,is_active:7,is_superuser:8
#    last_login:9,date_joined:10,roles

class UserLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'User',
                                   [('email', datastore_types.Email),
                                    ('first_name', str),
                                    ('last_name', str),
                                    ('password', str),
                                    ('is_active', bool),
                                    ('is_superuser', bool),
                                    ('last_login', lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S')),
                                    ('date_joined',lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S')),
                                    ('roles', str.split)
                                   ])   

loaders = [UserLoader]