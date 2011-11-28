from django.conf import settings
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'fbapp.views.canvas', name="fbapp.canvas"),
    url(r'^channel\.html$', 'fbapp.views.channel', name="fbapp.channel"),
)
