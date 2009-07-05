from google.appengine.ext import db, search
from auth.models import User
from traffic_log import constants;


class SpotConstraint(search.SearchableModel):
    dow   = db.IntegerProperty(verbose_name="Day of Week", choices=constants.DOW)
    dow_list = db.StringListProperty()
    hour  = db.IntegerProperty(verbose_name="Hour", choices=constants.HOUR)
    slot  = db.IntegerProperty(verbose_name="Spot", choices=constants.SLOT)
    spots = db.ListProperty(db.Key)

    def __init__(self, *args, **kw):
        key_name = "%d:%d:%d" % (kw['dow'], kw['hour'], kw['slot']) 
        search.SearchableModel.__init__(self, *args, **kw)


class Spot(search.SearchableModel):
    title     = db.StringProperty(verbose_name="Spot Title", required=True)
    body      = db.TextProperty(verbose_name="Spot Copy",  required=False)
    type      = db.StringProperty(verbose_name="Spot Type", required=True, choices=constants.SPOT_TYPE)
    expire_on = db.DateTimeProperty(verbose_name="Expire Date", required=False)
    created   = db.DateTimeProperty(auto_now_add=True)
    updated   = db.DateTimeProperty(auto_now=True)
    author    = db.ReferenceProperty(User)

    
    @property
    def constraints(self):
        return SpotConstraint.gql("where spots =:1 order by dow, hour, slot", self.key())

    def get_absolute_url(self):
        return '/traffic_log/spot/%s/' % self.key()


class TrafficLog(search.SearchableModel):
    log_date       = db.DateProperty()
    spot           = db.ReferenceProperty(Spot)
    readtime       = db.DateTimeProperty()
    reader         = db.ReferenceProperty(User, required=True)
    created        = db.DateTimeProperty(auto_now_add=True)
