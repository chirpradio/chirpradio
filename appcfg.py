#!/usr/bin/env python2.5

import os
import sys

def main(argv):
    from appengine_django import InstallAppengineHelperForDjango
    InstallAppengineHelperForDjango()

    # Superimpose the contents of the django-extras tree onto the django
    # module's namespace.
    import django
    django.__path__.append('django-extras')

    # Pull in CHIRP's monkey-patching of Django
    from django import _monkey_patch

    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        try:
            import settings # Assumed to be in the same directory.
        except ImportError:
            import sys
            sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to set the DJANGO_SETTINGS_MODULE environment variable.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
            sys.exit(1)
    
    from google.appengine.tools import appcfg
    appcfg.main(argv)

if __name__ == '__main__':
    main(sys.argv)