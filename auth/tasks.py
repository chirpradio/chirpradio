import logging

from django import http
from django.utils import simplejson as json

from auth import roles
from auth.models import User

log = logging.getLogger()


def sync_user(request):
    user = request.POST.get('user')
    if not user:
        return http.HttpResponseBadRequest()
    user = json.loads(user)

    qs = User.all().filter('external_id =', user['member_id'])
    users = qs.fetch(1)
    dj_user = None
    if len(users):
        dj_user = users[0]
    else:
        # No previously sync'd user exists.
        # Let's check by email to see if an old
        # user exists with the same email.
        qs = (User.all().filter('email =', user['email'])
                        .filter('external_id =', None))
        users = qs.fetch(1)
        if len(users):
            log.info('Linking user %s to ID %s' %
                     (user['email'], user['member_id']))
            dj_user = users[0]

    fields = {
        'first_name': user['name_first'],
        'last_name': user['name_last'],
        'email': user['email'],
        'dj_name': user['nick'],
        'external_id': user['member_id'],
        'is_active': True,
    }
    if not dj_user:
        fields['roles'] = [roles.DJ]
        dj_user = User(**fields)
    else:
        for k, v in fields.items():
            setattr(dj_user, k, v)
        if roles.DJ not in dj_user.roles:
            dj_user.roles.append(roles.DJ)
    dj_user.put()

    return http.HttpResponse('OK')


def deactivate_user(request):
    id = request.POST.get('external_id')
    if not id:
        log.info('external_id not found in POST')
        return http.HttpResponseBadRequest()
    qs = User.all().filter('external_id =', int(id))
    users = qs.fetch(1)
    if not len(users):
        log.info('no user exists with external_id %s' % id)
        # This is okay. We'll deactivate them next time.
        # Return a 200 here otherwise the task will be retried.
        return http.HttpResponse('No one deactivated')

    dj_user = users[0]
    dj_user.is_active = False
    dj_user.put()
    log.info('Deactivated user %s %s' % (dj_user, dj_user.email))

    return http.HttpResponse('OK')
