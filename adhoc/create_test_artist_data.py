
"""creates some artists and albums to manually test playlist autocompletion, etc."""

import sys
import os
import optparse

chirp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def startup_appengine(gae_path='/usr/local/google_appengine', clear_datastore=False):        
    sys.path.append(chirp_root)
    
    from appengine_django import InstallAppengineHelperForDjango
    InstallAppengineHelperForDjango()

    # Superimpose the contents of the django-extras tree onto the django
    # module's namespace.
    import django
    django.__path__.append('django-extras')

    # Pull in CHIRP's monkey-patching of Django
    from django import _monkey_patch
    
    # set up app engine paths
    sys.path.append(gae_path)
    sys.path.append(os.path.join(gae_path, "lib/django"))
    sys.path.append(os.path.join(gae_path, "lib/webob"))
    sys.path.append(os.path.join(gae_path, "lib/yaml/lib"))
    sys.path.append(os.path.join(gae_path, "lib/antlr3"))
    
    # set up dev app server
    from google.appengine.tools import dev_appserver
    config, explicit_matcher = dev_appserver.LoadAppConfig(chirp_root, {})
    
    from appengine_django.db.base import get_datastore_paths
    datastore_path, history_path = get_datastore_paths()
    
    if clear_datastore:
        print "clearing datastore"
    dev_appserver.SetupStubs(
        config.application, 
            clear_datastore = clear_datastore,
            datastore_path = datastore_path, 
            history_path = history_path, 
            login_url = None)

def main():
    parser = optparse.OptionParser(usage='%prog')
    parser.add_option('--clear-datastore', action='store_true')
    (options, args) = parser.parse_args()
    
    startup_appengine(clear_datastore=options.clear_datastore)
    
    from djdb import search, models
    import datetime

    idx = search.Indexer()
    
    # Create some test artists.
    art1 = models.Artist(name=u"Fall, The", parent=idx.transaction,
                         key_name="art1")
    art2 = models.Artist(name=u"Eno, Brian", parent=idx.transaction,
                         key_name="art2")
    # Create some test albums.
    alb1 = models.Album(title=u"This Nation's Saving Grace",
                        album_id=12345,
                        import_timestamp=datetime.datetime.now(),
                        album_artist=art1,
                        num_tracks=123,
                        parent=idx.transaction)
    alb2 = models.Album(title=u"Another Green World",
                        album_id=67890,
                        import_timestamp=datetime.datetime.now(),
                        album_artist=art2,
                        num_tracks=456,
                        parent=idx.transaction)
    for i, track_title in enumerate((   u"Spider And I", 
                                        u"Running To Tie Your Shoes", 
                                        u"Kings Lead Hat")):
        idx.add_track(models.Track(ufid="test3-%d" % i,
                                 album=alb2,
                                 sampling_rate_hz=44110,
                                 bit_rate_kbps=128,
                                 channels="mono",
                                 duration_ms=789,
                                 title=track_title,
                                 track_artist=art2,
                                 track_num=i+1,
                                 parent=idx.transaction))
    idx.add_artist(art1)
    idx.add_artist(art2)
    idx.add_album(alb1)
    idx.add_album(alb2)
    
    idx.save() # saves all objects
    
    print "created some artists and stuff"

if __name__ == '__main__':
    main()