from django.conf import settings
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'fbapp.views.canvas', name="fbapp.canvas"),
    url(r'^page_tab$', 'fbapp.views.page_tab', name="fbapp.page_tab"),
    url(r'^owa$', 'fbapp.views.open_web_app', name="fbapp.open_web_app"),
    url(r'^owa/chirpradio\.webapp$', 'fbapp.views.open_web_app_manifest',
        name="fbapp.open_web_app_manifest"),
    url(r'^channel\.html$', 'fbapp.views.channel', name="fbapp.channel"),
)
