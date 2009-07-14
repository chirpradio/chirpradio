"""
>>> import views, models, constants
>>> from chirpradio.auth import User, KeyStorage, roles
>>> from google.appengine.ext import db
>>> user = User(email='test')
>>> user.roles.append(roles.TRAFFIC_LOG_ADMIN)
>>> user.is_traffic_log_admin
True
>>> user.save()
datastore_types.Key.from_path(u'User', 1, _app=u'chirpradio')
>>> spot_key = models.Spot(title='test',body='body',type='Live Read Promo', author=user).put()
>>> constraint_key = models.SpotConstraint(dow=1,hour=1,slot=0).put()
>>> views.connectConstraintsAndSpot([constraint_key], spot_key)
>>> models.Spot.get(spot_key).constraints.count()
1
"""
