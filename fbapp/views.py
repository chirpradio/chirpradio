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


def absolutify(url):
    return '%s%s' % (settings.SITE_URL, url)


def canvas(request, template='fbapp/canvas.html', context={}):
    context = context.copy()
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

    # Bust javascript cache when developing:
    cache_stub = settings.DEBUG and str(time.time()) or ''
    channel_url = absolutify(reverse('fbapp.channel'))
    chirp_icon_url = '%s%sfbapp/img/Icon-50.png' % (settings.SITE_URL,
                                                    settings.MEDIA_URL)
    context.update(dict(cache_stub=cache_stub, app_id=app_id,
                        channel_url=channel_url,
                        chirp_icon_url=chirp_icon_url))
    context.setdefault('show_live_fb', True)
    context.setdefault('in_page_tab', False)
    context.setdefault('in_openwebapp', False)
    context.setdefault('root_div_id', 'fb-root')
    context.setdefault('connect_to_facebook', True)
    context.setdefault('api_source', 'facebook')
    context.setdefault('api_url', absolutify(reverse('fbapp.canvas')))
    response = render_to_response(template, context,
                                  context_instance=RequestContext(request))
    if not settings.DEBUG:
        hours = 5
        response['Cache-Control'] = 'public,max-age=%d' % int(3600 * hours)
    return response


def page_tab(request):
    return canvas(request, context={'in_page_tab': True})


def open_web_app(request):
    app_url = absolutify(reverse('fbapp.open_web_app'))
    return canvas(request, context={'show_live_fb': False,
                                    'root_div_id': 'owa-root',
                                    'in_openwebapp': True,
                                    'connect_to_facebook': False,
                                    'api_source': 'openwebapp',
                                    'app_url': app_url},
                  template='owa/app.html')


def open_web_app_manifest(request):
    response = render_to_response('owa/chirpradio.webapp', {},
                                  context_instance=RequestContext(request))
    response['Content-Type'] = 'application/x-web-app-manifest+json'
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
