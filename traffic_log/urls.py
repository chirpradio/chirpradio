from django.conf import settings
from django.conf.urls.defaults import *
from traffic_log.models import *
from django.views.generic import *

urlpatterns = patterns('',
    url(r'^/?$', 'traffic_log.views.index', name='traffic_log.index'),
    
    url(r'^spot/?$','traffic_log.views.listSpots', name='traffic_log.listSpots'),
    url(r'^spot/create/?$', 'traffic_log.views.createSpot', name='traffic_log.createSpot'),
    url(r'^spot/(?P<spot_key>[^\./]+)/read$', 'traffic_log.views.spotTextForReading',
                                                name="traffic_log.spotTextForReading"),
    (r'^spot/edit/(?P<spot_key>[^\.^/]+)$', 'traffic_log.views.editSpot'),
    url(r'^spot/delete/(?P<spot_key>[^\.^/]+)$', 'traffic_log.views.deleteSpot',
                                                name='traffic_log.deleteSpot'),
    (r'^spot/(?P<spot_key>[^\.^/]+)/?$', 'traffic_log.views.spotDetail'),
    url(r'^spot/(?P<spot_key>[^\.^/]+)/add-copy/?$', 'traffic_log.views.createEditSpotCopy',
                                                name='traffic_log.views.addCopyForSpot'),
    
    url(r'^spot-copy/create/?$', 'traffic_log.views.createEditSpotCopy', name='traffic_log.createSpotCopy'),
    url(r'^spot-copy/(?P<spot_copy_key>[^\./]+)/finish/?$', 'traffic_log.views.finishReadingSpotCopy',
                                                name="traffic_log.finishReadingSpotCopy"),
    url(r'^spot-copy/(?P<spot_copy_key>[^\./]+)/edit/?$', 'traffic_log.views.createEditSpotCopy',
                                                name="traffic_log.editSpotCopy"),
    url(r'^spot-copy/(?P<spot_copy_key>[^\./]+)/delete/?$', 'traffic_log.views.deleteSpotCopy',
                                                name="traffic_log.deleteSpotCopy"), 
                                                
    (r'^spot_constraint/delete/(?P<spot_constraint_key>[^\.^/]+)/spot/(?P<spot_key>[^\.^/]+)?$',
     'traffic_log.views.deleteSpotConstraint'),
    # kumar: commenting this out for now since the view function doesn't exist 
    # (r'^generate/(\d{4})/(\d{2})/(\d{2})','traffic_log.views.generateTrafficLog')
    )

