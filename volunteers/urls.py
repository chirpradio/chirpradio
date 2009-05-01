
"""URLs for the Volunteers app."""

from django.conf import settings
from django.conf.urls.defaults import *


urlpatterns = patterns('',
    (r'^meetings/?$', 
        'volunteers.views.meetings'),
    (r'^meetings/(\d+)/attendee/add/(\d+)\.json$', 
        'volunteers.views.add_meeting_attendee'),
    (r'^meetings/(\d+)/attendee/delete/(\d+)\.json$', 
        'volunteers.views.delete_meeting_attendee'),
    (r'^meetings/(\d{2})/(\d{2})/(\d{4})/track\.json$', 
        'volunteers.views.track_meeting'),
    (r'^search_users/?$', 
        'volunteers.views.search_users'),
    (r'^tasks/claim/(\d+)\.json$', 
        'volunteers.views.claim_task'),
    (r'^tasks/claim/?$', 
        'volunteers.views.show_tasks_for_claiming'),
)

#if settings.ENABLE_TEST_URLS:
#    urlpatterns += patterns('',
#        (r'^_ui_test_/claim_tasks_dev/?$', 
#            'volunteers._ui_test_.claim_tasks.claim_tasks_dev'),
#        (r'^_ui_test_/meetings_dev/?$', 
#            'volunteers._ui_test_.meetings.meetings_dev'),
#        (r'^_ui_test_/meetings_test/?$', 
#            'volunteers._ui_test_.meetings.meetings_test'),
#    )
