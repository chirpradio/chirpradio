
import subprocess
import glob
import os
import unittest

__all__ = ['TestJavascriptLint']

class TestJavascriptLint(unittest.TestCase):
    
    def test(self):
        heredir = os.path.dirname(__file__)
        root = os.path.normpath(os.path.join(heredir, '..', '..'))
        media = os.path.join(root, 'media')
        assert os.path.exists(media), "Possible miscalculation of root: %s" % root
        
        for filename in glob.glob("%s/*/js/*.js" % media):
            # jsl -nologo -nosummary -process media/playlists/js/playlists.js
            p = subprocess.Popen([
                'jsl',
                '-nologo',
                '-nosummary',
                '-process',
                filename
                ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
            returncode = p.wait()
            if returncode != 0:
                print "*"*40
                print p.stdout.read()
                print "*"*40
            self.assertEqual(returncode, 0, "Unexpected returncode: %s (see output above)" % returncode)