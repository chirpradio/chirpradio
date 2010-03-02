from django.conf import settings
from django.conf.urls.defaults import *
from traffic_log.models import *
from django.views.generic import *

urlpatterns = patterns('',
    url(r'^/?$', 'traffic_log.views.index', name='traffic_log.index'),
    (r'^spot/?$','traffic_log.views.listSpots'),
    url(r'^spot/create/?$', 'traffic_log.views.createSpot', name='traffic_log.createSpot'),
    url(r'^spot/(?P<spot_key>[^\./]+)/read$', 'traffic_log.views.spotTextForReading',
                                                name="traffic_log.spotTextForReading"),
    url(r'^spot/(?P<spot_key>[^\./]+)/finish/?$', 'traffic_log.views.finishSpot',
                                                name="traffic_log.finishSpot"),
    (r'^spot/edit/(?P<spot_key>[^\.^/]+)$', 'traffic_log.views.editSpot'),
    (r'^spot/delete/(?P<spot_key>[^\.^/]+)$', 'traffic_log.views.deleteSpot'),
    (r'^spot/(?P<spot_key>[^\.^/]+)/?$', 'traffic_log.views.spotDetail'),                       
    (r'^spot_constraint/delete/(?P<spot_constraint_key>[^\.^/]+)/spot/(?P<spot_key>[^\.^/]+)?$',
     'traffic_log.views.deleteSpotConstraint'),
    # kumar: commenting this out for now since the view function doesn't exist 
    # (r'^generate/(\d{4})/(\d{2})/(\d{2})','traffic_log.views.generateTrafficLog')
    )

