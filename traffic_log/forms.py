import logging

from django import forms
from google.appengine.ext.webapp import template
from google.appengine.ext.db import djangoforms

from traffic_log import constants, models
from common.autoretry import AutoRetry
from common import time_util

log = logging.getLogger()

class SpotForm(djangoforms.ModelForm):
    class Meta:
        model  = models.Spot
        fields = ('title', 'type')
        
class SpotCopyForm(djangoforms.ModelForm):
    
    spot_key = djangoforms.forms.ChoiceField(label="Spot", 
                                             required=True)
    underwriter = djangoforms.forms.CharField(required=False)
    expire_on = djangoforms.forms.DateTimeField(required=False,
                help_text=( "The following formats are recognized: "
                            "MM/DD/YYYY, MM/DD/YYYY 23:00, YYYY-MM-DD"))
    
    def __init__(self, *args, **kw):
        super(SpotCopyForm, self).__init__(*args, **kw)
        self['spot_key'].field.choices = [choice for choice in self._generate_spot_choices()]
    
    def clean_expire_on(self):
        expire_on = self.cleaned_data['expire_on']
        if expire_on:
            convert = True
            if self.instance:
                if self.instance.expire_on == expire_on:
                    # this means the datetime is in UTC format and so 
                    # we do not want to convert it.  In other words, the user 
                    # is editing spot copy but is not editing expire_on
                    convert = False
            if convert:
                # here we want to reflect the fact that the user has entered 
                # a date and time in CST so that it actually gets stored in UTC
                expire_on = expire_on.replace(tzinfo=time_util.central_tzinfo)
        return expire_on
        
    def _generate_spot_choices(self):
        q = models.Spot.all().order("title")
        for spot in AutoRetry(q):
            yield ( spot.key(),
                    "%s (%s)" % (spot.title, spot.type))
        
    class Meta:
        model  = models.SpotCopy
        fields = ('underwriter', 'body', 'expire_on')

class SpotConstraintForm(djangoforms.ModelForm):
    hourbucket = djangoforms.forms.ChoiceField(label="Hour Bucket",
                                               required=False,
                                               choices=constants.HOURBUCKET_CHOICES)
    dow_list   = djangoforms.forms.MultipleChoiceField(label="Day of Week",
                                                       required=True,
                                                       choices=constants.DOW_CHOICES)
    hour       = djangoforms.forms.ChoiceField(label="Hour",
                                               required=False,
                                               choices=constants.HOUR_CHOICES)
    slot       = djangoforms.forms.ChoiceField(label="Slot",
                                               required=True,
                                               choices=constants.SLOT_CHOICES)
    
    def clean_hourbucket(self):
        hour = self.cleaned_data.get('hour')
        hourbucket = self.cleaned_data.get('hourbucket')
        def empty(val):
            return val is None or val==""
        if empty(hour) and empty(hourbucket):
            raise forms.ValidationError("You must specify a recurring hour slot or select an exact hour")
            
        return self.cleaned_data['hourbucket']
        
    class Meta:
        model  = models.SpotConstraint
        fields = ('dow','hour','slot')


class TrafficLogForm(djangoforms.ModelForm):
    class Meta:
        model = models.TrafficLogEntry

class ReportForm(djangoforms.ModelForm):
    start_date = djangoforms.forms.DateField(label="Start Date", required=True)
    end_date = djangoforms.forms.DateField(label="End Date", required=True)
    type = djangoforms.forms.ChoiceField(label="Spot Type", required=False,
                                         choices=zip(constants.SPOT_TYPE_CHOICES, constants.SPOT_TYPE_CHOICES))
    underwriter = djangoforms.forms.CharField(label="Underwriter", required=False)
