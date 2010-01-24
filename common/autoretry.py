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

import time
import sys
import inspect
import logging
from functools import wraps
from google.appengine.runtime import apiproxy_errors
from google.appengine.datastore import datastore_pb
from google.appengine.api.datastore_errors import Timeout
from google.appengine.api.datastore_errors import TransactionFailedError
                

class AutoRetry(object):
    """Wrapper around any object that proxies methods and retries on failure.
    
    It is intended to workaround random GAE datastore timeout errors that 
    happen when executing queries.  While you can wrap any object you only 
    need to wrap a query object before calling a method that actually 
    executes a query.  Note that methods which return objects (e.g. chained calls) 
    do not automatically rewrap the returned object in AutoRetry for you.
    
    Example::
        
        query = User.all().filter('email =', email)
        all_users = AutoRetry(query).fetch(1000)
    
    See http://code.google.com/p/chirpradio/issues/detail?id=78 
    or search the GAE group discussion list for "datastore timeout" for more information.
    """
    
    def __init__(self, obj):
        if isinstance(obj, self.__class__):
            # This technically isn't a problem but 
            # it will increase the retry times and probably 
            # is a programming error that can be fixed
            raise ValueError("Cannot re-wrap in %r (with %r)" % (
                                self.__class__.__name__, obj))
        self.__obj = obj
    
    def __make_dispatcher(self, attr):
        method = getattr(self.__obj, attr)
        if not hasattr(method, '__name__'):
            # well, hmm, it seems that wraps() will raise an 
            # exception if a method does not have __name__
            method.__name__ = 'unnamed'
        @wraps(method)
        def dispatcher(*args, **kw):
            return self.__run_in_retry_loop(method, args, kw)
        return dispatcher
    
    __getitem__ = property(fget=lambda self: self.__make_dispatcher('__getitem__'))
    __iter__ = property(fget=lambda self: self.__make_dispatcher('__iter__'))

    def __getattr__(self, attr):
        return self.__make_dispatcher(attr)
    
    def __run_in_retry_loop(self, method, args, kw, attempts=5.0, interval=0.1, exponent=2.0):
        count = 0.0
        while 1:
            try:
                return method(*args, **kw)
            except (TransactionFailedError, Timeout), exc:
                etype, val, tb = sys.exc_info()
                exc_type = etype.__name__

                sleep = (exponent ** count) * interval
                count += 0.8
                if count > attempts: 
                    raise exc, None, tb

                msg = "Datastore %s: retry #%d in %s seconds.\n%s"
                if hasattr(method, '__name__'):
                    call_name = method.__name__
                else:
                    call_name = 'unknown'
                call = '%s(%s)' % (call_name, ', '.join([repr(a) for a in args]))
                logging.warning(msg % (exc_type, count, sleep, call))

                time.sleep(sleep)

