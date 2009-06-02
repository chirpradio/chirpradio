
"""Volunteer tracker views."""

# Python imports
import datetime
from datetime import timedelta
from decimal import Decimal
# Django imports
from django.db import transaction
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Context, loader, RequestContext
# App Engine imports
from google.appengine.ext import db
# CHIRP imports
from auth.models import User
from auth import roles
from auth.decorators import require_role
from common.decorators import respond_with_json
from volunteers import models


def require_volunteer_coordinator(handler):
    """A decorator that makes a page require the VOLUNTEER_COORDINATOR role."""
    return require_role(handler, roles.VOLUNTEER_COORDINATOR)


@require_volunteer_coordinator
def meetings(request):
    t = loader.get_template('volunteers/meetings.html')
    c = Context({
        'title': 'Meeting Attendance Tracker',
        'user': request.user,
        'root_path': '/' # just for the admin logout page
        })
    return HttpResponse(t.render(c))


# TODO(trow): This is totally broken.
@require_volunteer_coordinator
@respond_with_json
def add_meeting_attendee(request, meeting_id, user_id):
    m = Meeting.objects.get(id=meeting_id)
    m.attendees.add(User.objects.get(id=user_id))
    m.save()
    return { 'success': True }
    

# TODO(trow): This is totally broken.
@require_volunteer_coordinator
@respond_with_json
def delete_meeting_attendee(request, meeting_id, user_id):
    m = Meeting.objects.get(id=meeting_id)
    m.attendees.remove(User.objects.get(id=user_id))
    m.save()
    return { 'success': True }


# TODO(trow): This is totally broken.
@require_volunteer_coordinator
@respond_with_json
# TODO(trow): Should be YYYY MM DD
def track_meeting(request, mon, day, year):
    # this should add or edit a meeting:
    meeting_date = datetime.date(int(year), int(mon), int(day))
    q = Meeting.objects.filter(meeting_date=meeting_date)
    count = q.count()
    if count == 1:
        meeting = q[0]
    elif count == 0:
        meeting = Meeting(meeting_date=meeting_date)
        meeting.save()
    else:
        raise RuntimeError("Somehow there are %s meetings on %s"
                           % (count, meeting_date))
    
    return {
        'meeting_id': meeting.id,
        'attendees': [{ 'user_id': u.username, 'name': unicode(u) }
                      for u in meeting.attendees.all()]
        }


# TODO(trow): This is totally broken.
def show_tasks_for_claiming(request):
    t = loader.get_template('claim_tasks.html')
    events = [e for e in Event.objects.all().order_by("-start_date")]
    current_events = []
    now_date = datetime.datetime.now().date()
    for ev in events:
        # hide old events ...
        if ev.start_date + timedelta(days=ev.duration_days) >= now_date:
            current_events.append(ev)
    
    c = Context({
        'events': current_events,
        'title':'Claim A Task',
        'user': auth.get_user(request),
        'root_path': '/' # just for the admin logout page
    })
    return HttpResponse(t.render(c))
    

# TODO(trow): This is totally broken.
@transaction.commit_manually
@respond_with_json
def claim_task(request, task_id):
    try:
        task = get_object_or_404(Task, id=task_id)
        if len(task.claimed_by) == task.num_volunteers_needed:
            return {
                'success': False,
                'error': 'No more volunteers needed for task "%s"' % task
                }
        try:
            # TODO(trow): Broken
            volunteer = Volunteer.objects.get(user=request.user)
        except Volunteer.DoesNotExist, exc:
            raise ValueError(
                '%s is not a registered volunteer' % unicode(request.user))
        if request.user in task.claimed_by:
            return {
                'success': False,
                'error': 'You have already claimed task "%s"'  % task
                } 
        assignment = TaskAssignment()
        assignment.task = task
        assignment.volunteer = volunteer
        if task.potential_points:
            assignment.points = task.potential_points
        else:
            assignment.points = Decimal('1')
        assignment.save()
        
        template_vars = { 'event': task.for_event, 'task': task }
        message = loader.render_to_string('claim_task_email.txt',
                                          template_vars)
        msg = EmailMessage(subject='You have volunteered for a CHIRP task.',
                           body=message,
                           to=[current_user.email])
        msg.send(fail_silently=False)
    except:
        transaction.rollback()
        raise
    else:
        transaction.commit()

    return {
        'success': True,
        'user': {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            }
        }


def search_users(request):
    query = db.Query(User)
    # Force the user prefix into title case.  We do this to try to work
    # around the fact that our query is case-sensitive.
    user_prefix = request.GET['q'].title()
    # Restrict to the users whose first name begins with the prefix.
    query.filter('first_name >=', user_prefix)
    # ~ is the largest printable 7-bit character.  This is effectively
    # the same as a 'startswith'-style query.
    query.filter('first_name <', user_prefix + '~')
    # you can thank the jquery autocomplete plugin for 
    # the weird format of this list (pipe delimited).
    user_list = ['%s|%s' % (unicode(u), u.email) for u in query]
    return HttpResponse('\n'.join(user_list))
