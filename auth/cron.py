import base64
from datetime import datetime
import logging
import re
import xml.etree.ElementTree as ET

from django.core.urlresolvers import reverse
from django.utils import simplejson as json

from google.appengine.api import taskqueue, urlfetch

from auth.models import UserSync
from common import dbconfig
from common.utilities import cronjob


log = logging.getLogger()
ts = re.compile('''(?P<year>\d{4})(?P<mon>\d{2})(?P<day>\d{2})
                   (?P<hr>\d{2})(?P<min>\d{2})(?P<sec>\d{2})''',
                re.VERBOSE)


@cronjob
def sync_users(request):
    authstr = 'Basic %s' % base64.b64encode('%s:%s' %
        (dbconfig['chirpradio.member_api.user'],
         dbconfig['chirpradio.member_api.password']))
    resp = urlfetch.fetch(dbconfig['chirpradio.member_api.url'],
                          headers={'Authorization': authstr})
    if resp.status_code != 200:
        log.error(resp.content)
        raise ValueError('live site XML returned %s' % resp.status_code)
    root = ET.fromstring(resp.content)

    ts_parts = ts.match(root.find('last_updated').text)
    ts_parts = [int(x) for x in ts_parts.groups()]
    last_update = datetime(*ts_parts)
    log.info('chirpradio data last updated: %s' % last_update)

    try:
        sync = UserSync.all()[0]
        last_sync = sync.last_sync
    except IndexError:
        sync = UserSync()
        # Set to a random date in the past to force a new sync.
        last_sync = datetime(2012, 1, 1)
    if last_sync >= last_update:
        log.info('No need for sync')
        return

    stats = {'synced': 0, 'deactivated': 0}

    for vol in root.findall('current_volunteers/volunteer'):
        user = {'name_first': vol.find('name/first').text,
                'name_last': vol.find('name/last').text,
                'nick': vol.find('name/nick').text,
                'member_id': int(vol.find('member_id').text),
                'email': vol.find('email').text}
        taskqueue.add(url=reverse('auth.tasks.sync_user'),
                      params={'user': json.dumps(user)})
        stats['synced'] += 1

    for vol in root.findall('suspended_volunteers/volunteer'):
        taskqueue.add(url=reverse('auth.tasks.deactivate_user'),
                      params={'external_id': vol.find('member_id').text})
        stats['deactivated'] += 1

    sync.last_sync = last_update
    sync.put()
    log.info('Sync finished. Sychronized: %(synced)s; '
             'deactivated: %(deactivated)s' % stats)
