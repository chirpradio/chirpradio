
"""Views for the site landing page."""

from django import http
from django.template import RequestContext, loader


def landing_page(request):
    template = loader.get_template('landing_page/landing_page.html')
    ctx = RequestContext(request, {
            'title': 'Welcome to chirpradio',
            })
    return http.HttpResponse(template.render(ctx))
