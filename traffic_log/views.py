###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

import sys
import random
import datetime
import calendar
import logging

from google.appengine.ext import db

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import simplejson

import django.forms

from common.utilities import as_json, http_send_csv_file
from common import time_util
from common.autoretry import AutoRetry
import auth
from auth.models import User
from auth.roles  import DJ, TRAFFIC_LOG_ADMIN
from auth.decorators import require_role
from traffic_log import models, forms, constants

log = logging.getLogger()

def add_hour(base_hour):
    """Adds an hour to base_hour and ensures it's in range.
    
    Operates on 24 hour clock hours.
    """
    next_hour = base_hour + 1
    if next_hour == 25:
        next_hour = 0
    return next_hour

@require_role(DJ)
def index(request):
#    db.delete(models.TrafficLogEntry.all())
    now = time_util.chicago_now()
    today = now.date()
    current_hour = now.hour
    hour_plus1 = add_hour(current_hour)
    hour_plus2 = add_hour(hour_plus1)
    hour_plus3 = add_hour(hour_plus2)
    hours_to_show = [current_hour, hour_plus1, hour_plus2, hour_plus3]
    
    current_spots = (models.SpotConstraint.all()
                        .filter("dow =", today.isoweekday())
                        .filter("hour IN", hours_to_show)
                        .order("hour")
                        .order("slot"))
    
    def hour_position(s):
        return hours_to_show.index(s.hour)
        
    slotted_spots = sorted([s for s in AutoRetry(current_spots).fetch(10)], key=hour_position) 
    
    return render_to_response('traffic_log/index.html', dict(
            date=today,
            slotted_spots=slotted_spots
        ), context_instance=RequestContext(request))

@require_role(DJ)
def spotTextForReading(request, spot_key=None):
    spot = AutoRetry(models.Spot).get(spot_key)

    # Get random spot copy.
    dow, hour, slot = _get_slot_from_request(request)
    spot_copy, is_logged = spot.get_spot_copy(dow, hour, slot)

    # If spot copy has not already been read, construct url to finish.
    url = None
    if spot_copy and not is_logged:
        url = reverse('traffic_log.finishReadingSpotCopy', args=(spot_copy.key(),))
        url = "%s?hour=%d&dow=%d&slot=%d" % (url, hour, dow, slot)

    return render_to_response('traffic_log/spot_detail_for_reading.html', dict(
            spot_copy=spot_copy,
            url_to_finish_spot=url
        ), context_instance=RequestContext(request))

@require_role(DJ)
@as_json
def finishReadingSpotCopy(request, spot_copy_key=None):
    dow, hour, slot = _get_slot_from_request(request)
    
    # Check if a single spot constraint exists for the dow, hour, slot.
    q = (models.SpotConstraint.all()
                    .filter("dow =", dow)
                    .filter("hour =", hour)
                    .filter("slot =", slot))
    count = AutoRetry(q).count(1) 
    if count == 0:
        raise ValueError("No spot constraint found for dow=%r, hour=%r, slot=%r" % (
                                                                    dow, hour, slot))
    elif count > 1:
        # kumar: not sure if this will actually happen
        raise ValueError("Multiple spot constraints found for dow=%r, hour=%r, slot=%r" % (
                                                                    dow, hour, slot))
    
    constraint = AutoRetry(q).fetch(1)[0]

    spot_copy = AutoRetry(models.SpotCopy).get(spot_copy_key)

    # Check if spot has already been read (i.e., logged).
    today = time_util.chicago_now().date()
    q = (models.TrafficLogEntry.all()
                    .filter("log_date =", today)
                    .filter("spot =", spot_copy.spot)
                    .filter("dow =", dow)
                    .filter("hour =", hour)
                    .filter("slot =", slot))
    if AutoRetry(q).count(1):
        existing_logged_spot = AutoRetry(q).fetch(1)[0]
        raise RuntimeError("This spot %r at %r has already been read %s" % (
                    spot_copy.spot, constraint, existing_logged_spot.reader))

    # Remove spot copy from the spot's list.
    spot_copy.spot.finish_spot_copy()
	
    # Log spot read.
    logged_spot = models.TrafficLogEntry(
        log_date = today,
        spot = spot_copy.spot,
        spot_copy = spot_copy,
        dow = dow,
        hour = hour,
        slot = slot,
        scheduled = constraint,
        readtime = time_util.chicago_now(), 
        reader = auth.get_current_user(request)
    )
    AutoRetry(logged_spot).put()
    
    return {
        'spot_copy_key': str(spot_copy.key()), 
        'spot_constraint_key': str(constraint.key()),
        'logged_spot': str(logged_spot.key())
    }

@require_role(TRAFFIC_LOG_ADMIN)
def createSpot(request):
    user = auth.get_current_user(request)
    all_clear = False
    if request.method == 'POST':
        spot_form = forms.SpotForm(request.POST, {'author':user})
        constraint_form = forms.SpotConstraintForm(request.POST)
        if constraint_form.is_valid() and spot_form.is_valid():
            constraint_keys = saveConstraint(constraint_form.cleaned_data)
            spot = spot_form.save()
            spot.author = user
            AutoRetry(spot).put()
            connectConstraintsAndSpot(constraint_keys, spot.key())
            all_clear = True
    else:
        spot_form = forms.SpotForm()
        constraint_form = forms.SpotConstraintForm()

    if all_clear:
        return HttpResponseRedirect(reverse('traffic_log.listSpots'))

    return render_to_response('traffic_log/create_edit_spot.html', 
                  dict(spot=spot_form,
                       constraint_form=constraint_form,
                       Author=user,
                       formaction="/traffic_log/spot/create/"
                       ), context_instance=RequestContext(request))

@require_role(TRAFFIC_LOG_ADMIN)
def createEditSpotCopy(request, spot_copy_key=None, spot_key=None):
    if spot_copy_key:
        spot_copy = AutoRetry(models.SpotCopy).get(spot_copy_key)
        spot_key = spot_copy.spot.key() # so that dropdown box is selected when editing
        formaction = reverse('traffic_log.editSpotCopy', args=(spot_copy_key,))
    else:
        if spot_key:
            formaction = reverse('traffic_log.views.addCopyForSpot', args=(spot_key,))
        else:
            formaction = reverse('traffic_log.createSpotCopy')
        spot_copy = None
    user = auth.get_current_user(request)
    if request.method == 'POST':
        spot_copy_form = forms.SpotCopyForm(request.POST, {
                                'author':user, 
                                'spot_key':spot_key
                            }, instance=spot_copy)
        if spot_copy_form.is_valid():
            spot_copy = spot_copy_form.save()
            spot_copy.author = user
            spot_copy.spot = AutoRetry(models.Spot).get(spot_copy_form['spot_key'].data)
            
            # Add spot copy to spot's list of shuffled spot copies.
            spot_copy.spot.add_spot_copy(spot_copy)
            AutoRetry(spot_copy).put()
            
            return HttpResponseRedirect(reverse('traffic_log.listSpots'))
    else:
        spot_copy_form = forms.SpotCopyForm(initial={'spot_key':spot_key}, instance=spot_copy)

    return render_to_response('traffic_log/create_edit_spot_copy.html', 
                  dict(spot_copy=spot_copy_form,
                       formaction=formaction
                       ), context_instance=RequestContext(request))

@require_role(TRAFFIC_LOG_ADMIN)
def deleteSpotCopy(request, spot_copy_key=None):
    spot_copy = AutoRetry(models.SpotCopy).get(spot_copy_key)
    spot_copy.expire_on = time_util.chicago_now()
    AutoRetry(spot_copy).put()
    return HttpResponseRedirect(reverse('traffic_log.views.listSpots'))

@require_role(TRAFFIC_LOG_ADMIN)
def editSpot(request, spot_key=None):
    spot = AutoRetry(models.Spot).get(spot_key)
    user = auth.get_current_user(request)
    if request.method ==  'POST':
        spot_form = forms.SpotForm(request.POST)
        constraint_form = forms.SpotConstraintForm(request.POST)
        # check if spot is changed
        # check if new constraint to be added
        if spot_form.is_valid():
            for field in spot_form.fields.keys():
                setattr(spot,field,spot_form.cleaned_data[field])
                spot.author = user
                AutoRetry(models.Spot).put(spot)

        if constraint_form.is_valid():
            connectConstraintsAndSpot(
                saveConstraint(constraint_form.cleaned_data), spot.key()
                )
            
        return HttpResponseRedirect('/traffic_log/spot/%s'%spot.key())
    else:
        return render_to_response('traffic_log/create_edit_spot.html', 
                      dict(spot=forms.SpotForm(instance=spot),
                           spot_key=spot_key,
                           constraints=spot.constraints,
                           constraint_form=forms.SpotConstraintForm(),
                           edit=True,
                           dow_dict=constants.DOW_DICT,
                           formaction="/traffic_log/spot/edit/%s"%spot.key()
                           ), context_instance=RequestContext(request))


@require_role(TRAFFIC_LOG_ADMIN)
def deleteSpot(request, spot_key=None):
    spot = AutoRetry(models.Spot).get(spot_key)
    spot.active = False
    AutoRetry(spot).save()
    
    # remove the spot from its constraints:
    for constraint in AutoRetry(models.SpotConstraint.all().filter("spots IN", [spot.key()])):
        active_spots = []
        for spot_key in constraint.spots:
            if spot_key != spot.key():
                active_spots.append(spot_key)
        constraint.spots = active_spots
        AutoRetry(constraint).save()
        
    return HttpResponseRedirect('/traffic_log/spot')


@require_role(DJ)
def spotDetail(request, spot_key=None):
    spot = AutoRetry(models.Spot).get(spot_key)
    constraints = [forms.SpotConstraintForm(instance=x) for x in AutoRetry(spot.constraints)]
    form = forms.SpotForm(instance=spot)
    return render_to_response('traffic_log/spot_detail.html', {
            'spot':spot,
            'constraints':constraints,
            'dow_dict':constants.DOW_DICT
        }, context_instance=RequestContext(request))


@require_role(DJ)
def listSpots(request):
    spots = []
    # TODO(Kumar) introduce paging?
    for spot in AutoRetry(models.Spot.all().order('-created')).fetch(200):
        if spot.active is False:
            continue
        spots.append(spot)
    return render_to_response('traffic_log/spot_list.html', 
        {'spots':spots}, 
        context_instance=RequestContext(request))


def connectConstraintsAndSpot(constraint_keys,spot_key):
    for constraint in map(AutoRetry(models.SpotConstraint).get, box(constraint_keys)):
        #sys.stderr.write(",".join(constraint.spots))
        if spot_key not in constraint.spots:
            constraint.spots.append(spot_key)
            constraint.put()


def saveConstraint(constraint):
    dows = [ int(x) for x in constraint['dow_list'] ]
    
    keys = []
    if constraint['hourbucket'] != "":
        ## TODO(Kumar) I don't think this is such a good idea.  
        ## use split(",") and int() instead.
        hours = range(*eval(constraint['hourbucket']))
    else:
        hours = [int(constraint['hour'])]
    slot = int(constraint['slot'])
    for d in dows:
        for h in hours:
            name = ":".join([constants.DOW_DICT[d],str(h), str(slot)])
            obj  = AutoRetry(models.SpotConstraint).get_or_insert(name,dow=d,hour=h,slot=slot)
            if not obj.is_saved():
                AutoRetry(obj).put()
            keys.append(obj.key())
    return keys


@require_role(TRAFFIC_LOG_ADMIN)
def deleteSpotConstraint(request, spot_constraint_key=None, spot_key=None):
    ## XXX only delete if spot_key is none, otherwise just remove the
    ## constraint from the spot.constraints
    constraint = models.SpotConstraint.get(spot_constraint_key)
    if spot_key:
        constraint.spots.remove(models.Spot.get(spot_key).key())
        AutoRetry(constraint).save()
    else:
        ## XXX but will this ever really be needed (since you can't
        ## just create a constraint on it's own right now)?
        ## should just raise exception
        AutoRetry(constraint).delete()

    return HttpResponseRedirect('/traffic_log/spot/edit/%s'%spot_key)


## maybe we don't generate a weeks worth of logs and instead jit the logs per hour or per day?
def generateTrafficLogEntriesForWeek(request, year, month, day):
    for d in constants.DOW:
        next_day = datetime.datetime(int(year), int(month), int(day)) + datetime.timedelta(d)
        generateTrafficLogEntries(request, next_day.date())
        
    
def generateTrafficLogEntriesForDay(request, date=None):
    date = date if date else datetime.datetime.today().date()
    for hour in constants.HOUR:
        entries_for_hour = generateTrafficLogEntriesForHour(request, date, hour)


def generateTrafficLogEntriesForHour(request, datetime=None, hour=None):
    now = datetime if datetime else chicago_now()
    hour = hour if hour else now.hour
    log_for_hour = []
    for slot in constants.SLOT:
        log_for_hour.append(getOrCreateTrafficLogEntry(now.date, hour, slot))
            

def getOrCreateTrafficLogEntry(date, hour, slot):
    entry = models.TrafficLogEntry.gql(
        "where log_date = :1 and hour = :2 and slot = :3",
        date, hour, slot
        )
    
    if AutoRetry(entry).count():
        return AutoRetry(entry).get()
    else:
        constraint = models.SpotConstraint.gql(
            "where dow = :1 and hour = :2 and slot = :3",
            date.isoweekday(), hour, slot
            )
        if AutoRetry(constraint).count():
            constraint = AutoRetry(constraint).get()
            spot = randomSpot(constraint.spots)
            if spot:
                new_entry = models.TrafficLogEntry(
                    log_date  = date,
                    spot      = spot,
                    hour      = hour,
                    slot      = slot,
                    scheduled = constraint
                    )
                AutoRetry(new_entry).put()
                return new_entry
            else:
                return
 

def randomSpot(spotkeylist):
    #return models.Spot.get(random.choice(spotkeylist))
    return random.choice(spotkeylist)

                
def displayAndReadSpot(request, traffic_log_key):
    pass


def editTrafficLogEntry(request, key):
    pass


def deleteTrafficLogEntry(request, key):
    pass


def traffic_log(request, date):
    ## fetch TrafficLogEntry(s) for given date
    ## if none are found
    spots_for_date = TrafficLog.gql("where log_date=%s order by hour, slot"%date)
    return render_to_response('traffic_log/spot_list.html', 
        dict(spots=spots_for_date), 
        context_instance=RequestContext(request))

@require_role(TRAFFIC_LOG_ADMIN)
def report(request):
    entries = []
    if request.method == 'POST':
        report_form = forms.ReportForm(request.POST)
        if report_form.is_valid():
            query = (models.TrafficLogEntry.all()
                        .filter('log_date >= ', report_form.cleaned_data['start_date'])
                        .filter('log_date <= ', report_form.cleaned_data['end_date']))            
            filter_type = report_form.cleaned_data['type'] != "Spot Type"
            filter_underwriter = report_form.cleaned_data['underwriter'] != ""
            if filter_type or filter_underwriter:
                for entry in AutoRetry(query):
                    if (not filter_type or entry.spot.type == report_form.cleaned_data['type']) \
                       and (not filter_underwriter or entry.spot_copy.underwriter == report_form.cleaned_data['underwriter']):
                       entries.append(report_entry_to_csv_dict(entry))
            else:
                for entry in AutoRetry(query):
                    entries.append(report_entry_to_csv_dict(entry))
            if request.POST.get('download'):
                fields = ['readtime', 'dow', 'slot_time', 'underwriter', 'title', 'type', 'exerpt']
                fname = "chirp-traffic_log_%s_%s" % (report_form.cleaned_data['start_date'],
                                                     report_form.cleaned_data['end_date'])
                return http_send_csv_file(fname, fields, entries)
    else :
        end_date = datetime.datetime.now().date()
        start_date = end_date - datetime.timedelta(days=30)
        report_form = forms.ReportForm({'start_date': start_date, 'end_date': end_date})
    return render_to_response('traffic_log/report.html', 
                              {'form': report_form},
                              context_instance=RequestContext(request))

def report_entry_to_csv_dict(entry):
    return {    
        'readtime': time_util.convert_utc_to_chicago(entry.readtime),
        'dow': constants.DOW_DICT[entry.dow],                                       
        'underwriter': entry.spot_copy.underwriter,
        'slot_time': entry.scheduled.readable_slot_time,
        'title': entry.spot.title,
        'type': entry.spot.type,
        'exerpt': entry.spot_copy.body[:140]
    }

def box(thing):
    if isinstance(thing,list):
        return thing
    else:
        return [thing]

def _get_slot_from_request(request):
    dow = int(request.GET['dow'])
    if dow not in constants.DOW:
        raise ValueError("dow value %r is out of range" % dow)
    hour = int(request.GET['hour'])
    if hour not in constants.HOUR:
        raise ValueError("hour value %r is out of range" % hour)
    slot = int(request.GET['slot'])
    if slot not in constants.SLOT:
        raise ValueError("dow value %r is out of range" % slot)
    return dow, hour, slot
