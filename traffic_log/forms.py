from django import forms
from google.appengine.ext.webapp import template
from google.appengine.ext.db import djangoforms

from traffic_log import constants, models
from common.autoretry import AutoRetry


class SpotForm(djangoforms.ModelForm):
    class Meta:
        model  = models.Spot
        fields = ('title','type')
    

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
