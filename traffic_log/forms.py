from google.appengine.ext.webapp import template
from google.appengine.ext.db import djangoforms
from traffic_log import constants, models

class SpotForm(djangoforms.ModelForm):
    class Meta:
        model  = models.Spot
        fields = ('title','type','body','expire_on')
    
class SpotConstraintForm(djangoforms.ModelForm):
    hourbucket = djangoforms.forms.ChoiceField(label="Hour Bucket", required=False, choices=constants.HOURBUCKET_CHOICES)
    dow_list   = djangoforms.forms.MultipleChoiceField(label="Day of Week", required=True, choices=constants.DOW_CHOICES)
    hour       = djangoforms.forms.ChoiceField(label="Hour", required=False, choices=constants.HOUR_CHOICES)
    slot       = djangoforms.forms.ChoiceField(label="Slot", required=True, choices=constants.SLOT_CHOICES)

    class Meta:
        model  = models.SpotConstraint
        fields = ('dow','hour','slot')

class TrafficLogForm(djangoforms.ModelForm):
    class Meta:
        model = models.TrafficLog
