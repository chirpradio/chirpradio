
"""Configuration of admin forms.

The following code in chirp/urls.py tells Django to look for this module and load it::

    from django.contrib import admin
    admin.autodiscover()

"""

import datetime
from chirp.volunteers.models import *
from django.db import models as django_models
from django.contrib import admin
from django.contrib.admin.filterspecs import FilterSpec
from django import forms


class VolunteerAdminForm(forms.ModelForm):
    """Custom for for adding/editing Volunteers."""
    
    class Meta:
        model = Volunteer
    
    def clean_user(self):
        user = self.cleaned_data['user']
        errors = []
        if not user.is_staff:
            errors.append(
                "User %s cannot be a volunteer because he/she has not been "
                "marked with Staff status (you can fix this in Home > Auth > "
                "Users under the Permissions section)" % user)
        if 'Volunteer' not in [c.name for c in user.groups.all()]:
            errors.append(
                "User %s cannot be a volunteer because he/she is not in the "
                "Volunteer group (You can fix this in Home > Auth > Users "
                "under the Groups section)" % (user))
        if errors:
            raise forms.ValidationError(errors)
        return user

class VolunteerAdmin(admin.ModelAdmin):
    """Configures administration of Volunteers"""
    
    form = VolunteerAdminForm
    list_display = [
        'first_name', 'last_name', 'email', 'phone_1', 'phone_2']
    search_fields = ['user__first_name', 'user__last_name']
admin.site.register(Volunteer, VolunteerAdmin)

class TaskStatusAdmin(admin.ModelAdmin):
    """Configures administration of task status"""
    
admin.site.register(TaskStatus, TaskStatusAdmin)

class TaskTypeAdmin(admin.ModelAdmin):
    """Configures administration of task type"""
    
    search_fields = ['short_description', 'description']
    
admin.site.register(TaskType, TaskTypeAdmin)

class TaskForm(forms.ModelForm):
    """Custom form for adding/editing tasks."""

    class Meta:
        model = Task

    def clean_start_time(self):
        event = self.cleaned_data.get('for_event')
        start_time = self.cleaned_data.get('start_time')
        # If this task has a start time and is part of an event,
        # make sure that the start time is during the event.
        if event and start_time:
            event_start_date = event.start_date
            event_duration = datetime.timedelta(days=event.duration_days)
            event_end_date = event_start_date + event_duration
            if start_time.date() < event_start_date:
                raise forms.ValidationError(
                    'Task cannot start before the event begins')
            if start_time.date() >= event_end_date:
                raise forms.ValidationError(
                    'Task cannot start after the event has ended')
        return start_time

    def clean_duration_minutes(self):
        event = self.cleaned_data.get('for_event')
        start_time = self.cleaned_data.get('start_time')
        duration_minutes = self.cleaned_data.get('duration_minutes')
        # If this task is part of an event, make sure that it ends
        # during the event.
        if event and start_time and duration_minutes:
            task_duration = datetime.timedelta(minutes=duration_minutes)
            end_time = start_time + task_duration
            # A one-second "grace period" to avoid boundary effects.
            end_time -= datetime.timedelta(seconds=1)
            event_start_date = event.start_date
            event_duration = datetime.timedelta(days=event.duration_days)
            event_end_date = event_start_date + event_duration
            if end_time.date() >= event_end_date:
                raise forms.ValidationError(
                    'Task duration extends past the end of the event')
        return duration_minutes


class TaskAdmin(admin.ModelAdmin):
    """Configures administration of tasks"""
    
    form = TaskForm
    list_display = ['task_type', 'description']
    search_fields = [
        'task_type__short_description', 'task_type__description', 'description', 
        'volunteer__user__first_name', 'volunteer__user__last_name']
                     
admin.site.register(Task, TaskAdmin)

class TaskAssignmentAdmin(admin.ModelAdmin):
    """Configures administration of task assignments"""
    
    list_display = ['task', 'volunteer']
    
admin.site.register(TaskAssignment, TaskAssignmentAdmin)

class CommitteeAdmin(admin.ModelAdmin):
    """Configures administration of committees"""
    
admin.site.register(Committee, CommitteeAdmin)

class EventAdmin(admin.ModelAdmin):
    """Configures administration of events"""

admin.site.register(Event, EventAdmin)

