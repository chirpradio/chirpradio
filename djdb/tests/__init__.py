###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the 'License');
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an 'AS IS' BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

import os
import unittest


def suite():
    """Assemble a test suite from all of this file's *_test.py files."""
    # Find all of the test files in this directory and use them to
    # build up a list of modules.
    all_test_modules =["%s.%s" % (__name__, fn[:-3])
                       for fn in os.listdir(os.path.dirname(__file__))
                       if fn.endswith("_test.py")]
    # Now create a test suite and use it to aggregate all of the tests
    # from our various files.
    my_suite = unittest.TestSuite()
    for module in all_test_modules:
        my_suite.addTest(unittest.defaultTestLoader.loadTestsFromName(module))
    return my_suite
