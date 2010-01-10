
import sys
import subprocess
import glob
import os
import unittest

__all__ = ['TestJavascriptLint']

class NoSuchCommand(OSError):
    pass

class TestJavascriptLint(unittest.TestCase):
    
    def test(self):
        heredir = os.path.dirname(__file__)
        root = os.path.normpath(os.path.join(heredir, '..', '..'))
        media = os.path.join(root, 'media')
        assert os.path.exists(media), "Possible miscalculation of root: %s" % root
        
        for filename in glob.glob("%s/*/js/*.js" % media):
            # in macports:
            # sudo port install javascript-lint
            prog = 'jsl'
            try:
                p = subprocess.Popen([
                    prog,
                    '-nologo',
                    '-nosummary',
                    '-process',
                    filename
                    ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
            except OSError, exc:
                etype, val, tb = sys.exc_info()
                raise NoSuchCommand(
                    "%s: %s (please make sure javascript-lint `%s` exists and is in your $PATH)" % (
                                                                    etype.__name__, val, prog)), None, tb
                
            returncode = p.wait()
            if returncode != 0:
                print "*"*40
                print p.stdout.read()
                print "*"*40
            self.assertEqual(returncode, 0, "Unexpected returncode: %s (see output above)" % returncode)