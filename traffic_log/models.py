from google.appengine.ext import db
from traffic_log import constants;


class SpotConstraint(db.Model):
    dow   = db.IntegerProperty(verbose_name="Day of Week", choices=constants.DOW)
    dow_list = db.StringListProperty()
    hour  = db.IntegerProperty(verbose_name="Hour", choices=constants.HOUR)
    slot  = db.IntegerProperty(verbose_name="Spot", choices=constants.SLOT)
    spots = db.ListProperty(db.Key)
    
    def __init__(self, *args, **kw):
        kw['key_name'] = ":".join([ constants.DOW_DICT[kw['dow']], str(kw['hour']), str(kw['slot']) ])
        db.Model.__init__(self, *args, **kw)


class Spot(db.Model):
    title     = db.StringProperty(verbose_name="Spot Title", required=True)
    body      = db.StringProperty(verbose_name="Spot Copy", multiline=True, required=False)
    type      = db.StringProperty(verbose_name="Spot Type", required=True, choices=constants.SPOT_TYPE)
    expire_on = db.DateTimeProperty(verbose_name="Expire Date", required=False)
    created   = db.DateTimeProperty(auto_now_add=True)
    updated   = db.DateTimeProperty(auto_now=True)
    author    = db.UserProperty()
    
    @property
    def constraints(self):
        return SpotConstraint.gql("where spots =:1", self.key())

    def get_absolute_url(self):
        return '/traffic_log/spot/%s/' % self.key()


class TrafficLog(db.Model):
    log_date       = db.DateProperty()
    spot           = db.ReferenceProperty(Spot)
    readtime       = db.DateTimeProperty()
    reader         = db.UserProperty()
    created        = db.DateTimeProperty(auto_now_add=True)
