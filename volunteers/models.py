
"""Data model for volunteers app."""

from datetime import datetime, timedelta
from django.utils.dateformat import format as dateformat, time_format
from google.appengine.ext import db
from auth.models import User


class Meeting(db.Model):
    date = db.DateProperty(required=True)
    location = db.StringProperty()


class MeetingAttendance(db.Model):
    meeting = db.ReferenceProperty(Meeting, required=True,
                                   collection_name='attendance_join')
    user = db.ReferenceProperty(User, required=True,
                                collection_name='all_meetings_join')


class Committee(db.Model):
    """A CHIRP committee that a Volunteer belongs to."""
    name = db.StringProperty()

    # TODO(trow): Should there be a "chair" property?
    
    def __unicode__(self):
        return self.name


class CommitteeMember(db.Model):
    commitee = db.ReferenceProperty(Committee, required=True,
                                    collection_name='membership_join')
    user = db.ReferenceProperty(User, required=True,
                                collection_name='all_committees_join')


def get_dues_paid_year_choices():
    """Returns choices for the Dues Paid form field.
    
    Returns tuple of tuples.  I.E. ::
            
        (('2007', '2007'), ('2008', '2008'))
    """
    years = []
    y = int(datetime.now().strftime('%Y'))
    while y >= 2008:
        years.append((str(y),str(y)))
        y = y - 1 
    return years

    
class VolunteerInfo(db.Model):
    """A volunteer user."""
    user = db.ReferenceProperty(User, required=True)

    emergency_contact_name = db.StringProperty()
    emergency_contact_number = db.PhoneNumberProperty()
    emergency_contact_relationship = db.StringProperty()

    # TODO(trow): Removed dj_shift_day and dj_shift_time_slot, as that
    # model doesn't seem rich enough --- it doesn't account for the
    # possibility of irregular shifts.
    vol_info_sheet = db.BooleanProperty()
    dues_paid_year = db.IntegerProperty()
    dues_waived = db.BooleanProperty()

    phone_1 = db.PhoneNumberProperty()
    phone_2 = db.PhoneNumberProperty()
    address = db.PostalAddressProperty()

    day_job = db.StringProperty()
    availability = db.StringProperty()
    skills = db.StringProperty()

    has_a_car = db.BooleanProperty()
    has_equipment = db.BooleanProperty()
    can_dj_events = db.BooleanProperty()
    can_fix_stuff = db.BooleanProperty()
    knows_computers = db.BooleanProperty()
    
    # TODO(trow): These should probably be part of the form.
    discovered_chirp_by_choices = (
        'Friends',
        'CHIRP website',
        'Another website',
        'News article',
        'Record Fair',
        'WLUW',
        'Table at a Festival or Show',
        'Other'
    )
    discovered_chirp_by = db.StringProperty(
        choices=discovered_chirp_by_choices)
        
    discovered_chirp_by_details = db.StringProperty()

    notes = db.TextProperty()
    
    def __unicode__(self):
        return "%s (%s %s)" % (self.user.username, 
                               self.user.first_name, 
                               self.user.last_name)


class Event(db.Model):
    """Describes an event."""
    # A string describing this event.
    name = db.StringProperty(required=True)
    # Where the event will take place.
    location = db.StringProperty()
    start_date = db.DateTimeProperty()
    # TODO(trow): Require this to be >= 1.
    duration_days = db.IntegerProperty(default=1,
                                       verbose_name='event duration (days)')
    tasks_can_be_claimed = db.BooleanProperty(default=False, 
                                              verbose_name='tasks are ready to be claimed')

    def __unicode__(self):
        """Returns a human-readable version of an Event."""
        if not self.start_date:
            return self.name
        if self.duration_days == 1:
            return '%s (%s)' % (self.name, self.start_date)
        return '%s (%d days, starts %s)' % (self.name, self.duration_days,
                                            self.start_date)
    
    @property
    def tasks(self):
        raise NotImplementedError("TODO")
        # tasks = []
        # if self.tasks_can_be_claimed:
        #     tasks = [t for t in self.task_set.all().order_by("start_time")]
        # return tasks
    

class TaskType(db.Model):
    """The type of a task performed by a volunteer"""

    short_description = db.StringProperty()

    important_note = db.StringProperty()

    description = db.TextProperty()
    
    def __unicode__(self):
        return self.short_description

    
class Task(db.Model):
    """The task performed by a volunteer.
    
    This task may be assigned multiple times
    """

    for_committee = db.ReferenceProperty(Committee)
    for_event = db.ReferenceProperty(Event)
    task_type = db.ReferenceProperty(TaskType)

    # TODO(trow): Enforce that this is > 0.
    duration_minutes = db.IntegerProperty()

    # TODO(trow): Enforce that this is > 0.
    num_volunteers_needed = db.IntegerProperty(default=1, required=True)

    # TODO(trow): Enforce that this is > 0.
    potential_points = db.IntegerProperty()

    description = db.TextProperty()
    
    @property
    def claim_task_url(self):
        return "/chirp/tasks/claim/%s.json" % self.id
    
    @property
    def end_time(self):
        if not self.start_time or not self.duration_minutes:
            raise ValueError(
                "Cannot access self.end_time because this task does "
                "not have a start_time or duration value.")
        return self.start_time + timedelta(minutes=self.duration_minutes)
    
    @property
    def claim_prompt(self):
        return (
            "You are about to commit to %s." % self.__unicode__())
    
    @property
    def claimed_by(self):
        # return users assigned to this task (includes completed tasks)
        return [asn.volunteer.user for asn in 
                self.taskassignment_set.filter(
                        status__in=TaskStatus.objects.filter(
                                        status__in=['Assigned','Completed']))]
                            
    def __unicode__(self):
        task = self.task_type.__unicode__()
        descr = self.description or self.task_type.description
        if descr:
            task = "%s: %s" % (task, descr)
        if self.start_time:
            task = "%s on %s from %s - %s" % (
                        task, 
                        dateformat(self.start_time, "D M jS"),
                        time_format(self.start_time, "g:i a"),
                        time_format(self.end_time, "g:i a"))
            
        return task


class TaskAssignment(db.Model):
    """A task assigned to a Volunteer."""
    
    task = db.ReferenceProperty(Task, required=True,
                                collection_name="all_task_assignments")

    volunteer = db.ReferenceProperty(User, required=True,
                                     collection_name="all_task_assignments")

    # TODO(trow): Enforce that this is >= 0.
    points = db.IntegerProperty()

    STATUS_ASSIGNED = "Assigned"
    STATUS_COMPLETED = "Completed"
    ALL_STATUSES = (STATUS_ASSIGNED, STATUS_COMPLETED)
    status = db.CategoryProperty(choices=ALL_STATUSES)
    
    def __unicode__(self):
        return "%s assigned to %s" % (self.task, self.volunteer)

        
    
    
    
