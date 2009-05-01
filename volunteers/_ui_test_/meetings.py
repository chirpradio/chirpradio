
"""This is a stub view that can be used to 
develop or test the Meeting Tracker JavaScript 
functionality without hitting the actual database.

"""

from django.template import Context, loader
from django.http import HttpResponse
from chirp.utils import as_json

def meetings_dev(request):
    t = loader.get_template('meetings.html')
    c = Context({
        'extra_js_scripts': [
            '/local_site_media/js/chirp/meetings_stub_urls.js'
        ],
        'title':'Meeting Attendance Tracker'
    })
    return HttpResponse(t.render(c))

def meetings_test(request):
    t = loader.get_template('meetings.html')
    c = Context({
        'extra_js_scripts': [
            '/local_site_media/js/jquery/qunit/testrunner.js',
            '/local_site_media/js/jquery/plugins/jquery.simulate.js',
            '/local_site_media/js/chirp/meetings_stub_urls.js',
            '/local_site_media/js/chirp/meetings_test.js'
        ],
        'extra_stylesheets': [
            '/local_site_media/js/jquery/qunit/testsuite.css',
        ],
        'title':'Meeting Attendance Tracker'
    })
    return HttpResponse(t.render(c))