from django.http import HttpResponse, HttpResponseRedirect
#from django.shortcuts import render_to_response
from django.conf import settings
from django.template import Context, RequestContext, loader
from django.utils import simplejson
import sys
import random
import datetime

import auth
from auth.models import User
from auth.roles  import DJ, TRAFFIC_LOG_ADMIN
from auth.decorators import require_role
from traffic_log import models, forms, constants


def render(request, template, payload):
    template = loader.get_template(template)
    return HttpResponse(template.render(RequestContext(request, payload)))

@require_role(DJ)
def index(request):
    spots = models.Spot.all().order('-created').fetch(20)
    return render(request, 'traffic_log/index.html', dict(spots=spots))

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
            spot.put()
            connectConstraintsAndSpot(constraint_keys, spot.key())
            all_clear = True

        elif spot_form.is_valid():
            spot = spot_form.save()
            
            all_clear = True
            
    else:
        spot_form = forms.SpotForm()
        constraint_form = forms.SpotConstraintForm()

    if all_clear:
        return HttpResponseRedirect('/traffic_log/spot/%s'%spot.key())          

    return render(request, 'traffic_log/create_edit_spot.html', 
                  dict(spot=spot_form,
                       constraint_form=constraint_form,
                       Author=user,
                       formaction="/traffic_log/spot/create/"
                       )
                  )


@require_role(TRAFFIC_LOG_ADMIN)
def editSpot(request, spot_key=None):
    spot = models.Spot.get(spot_key)
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
                models.Spot.put(spot)

        if constraint_form.is_valid():
            connectConstraintsAndSpot(
                saveConstraint(constraint_form.cleaned_data), spot.key()
                )
            
        return HttpResponseRedirect('/traffic_log/spot/%s'%spot.key())
    
    else:
        return render(request, 'traffic_log/create_edit_spot.html', 
                      dict(spot=forms.SpotForm(instance=spot),
                           spot_key=spot_key,
                           constraints=spot.constraints,
                           constraint_form=forms.SpotConstraintForm(),
                           edit=True,
                           dow_dict=constants.DOW_DICT,
                           formaction="/traffic_log/spot/edit/%s"%spot.key()
                           )
                      )


@require_role(TRAFFIC_LOG_ADMIN)
def deleteSpot(request, spot_key=None):
    models.Spot.get(spot_key).delete()
    return HttpResponseRedirect('/traffic_log/spot')


def spotDetail(request, spot_key=None):
    spot = models.Spot.get(spot_key)
    constraints = [forms.SpotConstraintForm(instance=x) for x in spot.constraints]
    form = forms.SpotForm(instance=spot)
    return render(request, 'traffic_log/spot_detail.html',
                  {
                    'spot':spot,
                    'constraints':constraints,
                    'dow_dict':constants.DOW_DICT
                    }
                  )


def listSpots(request):
    spots = models.Spot.all().order('-created').fetch(20)
    return render(request, 'traffic_log/spot_list.html', {'spots':spots})


def connectConstraintsAndSpot(constraint_keys,spot_key):
    for constraint in map(models.SpotConstraint.get, box(constraint_keys)):
        #sys.stderr.write(",".join(constraint.spots))
        if spot_key not in constraint.spots:
            constraint.spots.append(spot_key)
            constraint.put()


def saveConstraint(constraint):
    dows = [ int(x) for x in constraint['dow_list'] ]
    
    keys = []
    if constraint['hourbucket'] != "":
        hours = range(*eval(constraint['hourbucket']))
    else:
        hours = [int(constraint['hour'])]
    slot = int(constraint['slot'])
    for d in dows:
        for h in hours:
            name = ":".join([constants.DOW_DICT[d],str(h), str(slot)])
            obj  = models.SpotConstraint.get_or_insert(name,dow=d,hour=h,slot=slot)
            if not obj.is_saved():
                obj.put()
            keys.append(obj.key())
    return keys


@require_role(TRAFFIC_LOG_ADMIN)
def deleteSpotConstraint(request, spot_constraint_key=None, spot_key=None):
    ## XXX only delete if spot_key is none, otherwise just remove the
    ## constraint from the spot.constraints
    constraint = models.SpotConstraint.get(spot_constraint_key)
    if spot_key:
        constraint.spots.remove(models.Spot.get(spot_key).key())
        constraint.save()
    else:
        ## XXX but will this ever really be needed (since you can't
        ## just create a constraint on it's own right now)?
        ## should just raise exception
        constraint.delete()

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
    now = datetime if datetime else datetime.datetime.now()
    hour = hour if hour else now.hour
    log_for_hour = []
    for slot in constants.SLOT:
        log_for_hour.append(getOrCreateTrafficLogEntry(now.date, hour, slot))
            

def getOrCreateTrafficLogEntry(date, hour, slot):
    entry = models.TrafficLogEntry.gql(
        "where log_date = :1 and hour = :2 and slot = :3",
        date, hour, slot
        )
    
    if entry.count():
        return entry.get()
    else:
<<<<<<< local
        constraint = models.SpotConstraint.gql(
            "where dow = :1 and hour = :2 and slot = :3",
            date.isoweekday(), hour, slot
            )
        
=======
        constraint = models.SpotConstraint.gql("where dow = :1 and hour = :2 and slot = :3",date.isoweekday(),hour,slot)
>>>>>>> other
        if constraint.count():
            constraint = constraint.get()
            spot = randomSpot(constraint.spots)
            if spot:
                new_entry = models.TrafficLogEntry(
                    log_date  = date,
                    spot      = spot,
                    hour      = hour,
                    slot      = slot,
                    scheduled = constraint
                    )
                new_entry.put()
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
    return render(request, 'traffic_log/index.html', dict(spots=spots_for_date))

def box(thing):
    if isinstance(thing,list):
        return thing
    else:
        return [thing]
    
