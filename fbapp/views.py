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
    app_id = dbconfig['facebook.app_key']
    payload = None
    if (request.POST.get('signed_request') and
        '.' in request.POST['signed_request']):
        signature, b64blob = request.POST['signed_request'].split('.')[:2]
        if len(b64blob) % 4 != 0:
            # Python requires padding for 4 byte chunks.
            # http://stackoverflow.com/questions/3302946/how-to-base64-url-decode-in-python
            b64blob = '%s==' % b64blob
        try:
            payload = simplejson.loads(base64.b64decode(b64blob))
        except (TypeError, ValueError), exc:
            log.exception('Invalid payload:')
        # TODO(Kumar) validate payload w/ signature
    log.debug(payload)

    in_page_tab = payload and 'page' in payload  # otherwise in app canvas
    if not request.POST:
        # Well, due to some SSL weirdness, page tabs sometimes do not
        # get POST requests.  Look for:
        # http://static.ak.facebook.com/platform/page_proxy.php
        if 'page_proxy' in str(request.META.get('HTTP_REFERER', '')):
            in_page_tab = True

    # Bust javascript cache when developing:
    cache_stub = settings.DEBUG and str(time.time()) or ''
    channel_url = settings.SITE_URL + reverse('fbapp.channel')
    response = render_to_response('fbapp/canvas.fbml',
                                  dict(cache_stub=cache_stub, app_id=app_id,
                                       channel_url=channel_url,
                                       in_page_tab=in_page_tab),
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
