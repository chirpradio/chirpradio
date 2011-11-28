import base64
import logging
import time
import urllib

from django import http
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import simplejson

from common import dbconfig


log = logging.getLogger()


def canvas(request):
    app_id = dbconfig['FACEBOOK_APP_ID']
    # Bust javascript cache when developing:
    cache_stub = settings.DEBUG and str(time.time()) or ''
    channel_url = settings.SITE_URL + reverse('fbapp.channel')
    response = render_to_response('fbapp/canvas.fbml',
                                  dict(cache_stub=cache_stub, app_id=app_id,
                                       channel_url=channel_url),
                                  context_instance=RequestContext(request))
    if not settings.DEBUG:
        hours = 5
        response['Cache-Control'] = 'public,max-age=%d' % int(3600 * hours)
    return response


def channel(request):
    response = render_to_response('fbapp/channel.html', {},
                                  context_instance=RequestContext(request))
    expire = int(3600 * 24)  # 24 hours in seconds
    response['Cache-Control'] = 'public,max-age=%d' % expire
    # response['Expires'] = datetime.now() + timedelta(seconds=expire)
    return response
