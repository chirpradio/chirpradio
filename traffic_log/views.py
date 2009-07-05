from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.conf import settings
from django.template import Context, loader
from django.utils import simplejson
import sys

from traffic_log import models, forms, constants
from auth.models import User

def render(template, payload):
    return render_to_response(template, payload)

def index(request):
    spots = models.Spot.all().order('-created').fetch(20)
    return render('traffic_log/index.html', dict(spots=spots))

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

def editSpotConstraint(request,spot_constraint_key=None):
    constraint = models.SpotConstraint.get(spot_constraint_key)
    
    if request.method ==  'POST':
        constraint_form = forms.SpotConstraintForm(request.POST)

        if constraint_form.is_valid():
            for field in constraint_form.cleaned_data.keys():
                value = constraint_form.cleaned_data[field]
                value = int(value) if value !='' else ''
                setattr(constraint,field,value)

            constraint.put()
            return HttpResponseRedirect('/traffic_log/spot_constraint')

        constraints = [constraint_form]

    else:
        constraints=[forms.SpotConstraintForm(instance=constraint)]

    return render('traffic_log/create_edit_spot_constraint.html', 
                  dict(constraints=constraints,
                       edit=True,
                       formaction="/traffic_log/spot_constraint/edit/%s"%constraint.key()
                       )
                  )


def deleteSpotConstraint(request, spot_constraint_key=None, spot_key=None):
    """ delete a constraint out of the store or remove a spot from a
    constraints spot list
    >>> spot = models.Spot(title='test', body='test',
    """
    ## XXX only delete if spot_key is none, otherwise just remove the
    ## constraint from the spot.constraints
    constraint = models.SpotConstraint.get(spot_constraint_key)
    if spot_key:
        constraint.spots.remove(models.Spot.get(spot_key).key())
        constraint.save()
    else:
        ## XXX but will this ever really be needed (since you can't
        ## just create a constraint on it's own right now)?
        constraint.delete()

    return HttpResponseRedirect('/traffic_log/spot/edit/%s'%spot_key)

def listSpotConstraints(request):
    constraints = models.SpotConstraint.all().order('dow').order('hour').order('slot')
    return render('traffic_log/view_constraints.html', {'constraints':constraints, 'dow_dict':constants.DOW_DICT})

## XXX crap alert
## I'm not checking for errors when data is being saved
## secondly I'm using a status flag...
## 
def createSpot(request):
    user = User.get_by_email("%s"%request.user)
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

        elif spot_form.is_valid() and not constraint_form.data.values():
            
            spot_form.save()
            all_clear = True
    else:
        spot_form = forms.SpotForm()
        constraint_form = forms.SpotConstraintForm()

    if all_clear:
        return HttpResponseRedirect('/traffic_log/spot/')          

    return render('traffic_log/create_edit_spot.html', 
                  dict(spot=spot_form,
                       constraint_form=constraint_form,
                       author=user,
                       formaction="/traffic_log/spot/create/"
                       )
                  )


def editSpot(request, spot_key=None):
    spot = models.Spot.get(spot_key)
    if request.method ==  'POST':
        spot_form = forms.SpotForm(request.POST)
        constraint_form = forms.SpotConstraintForm(request.POST)
        # check if spot is changed
        # check if new constraint to be added
        if spot_form.is_valid():
            for field in spot_form.fields.keys():
                setattr(spot,field,spot_form.cleaned_data[field])
                models.Spot.put(spot)

        if constraint_form.is_valid():
            connectConstraintsAndSpot(
                saveConstraint(constraint_form.cleaned_data), spot.key()
                )
            
        return HttpResponseRedirect('/traffic_log/spot/')
    
    else:
        return render('traffic_log/create_edit_spot.html', 
                      dict(spot=forms.SpotForm(instance=spot),
                           spot_key=spot_key,
                           constraints=spot.constraints,
                           constraint_form=forms.SpotConstraintForm(),
                           edit=True,
                           dow_dict=constants.DOW_DICT,
                           formaction="/traffic_log/spot/edit/%s"%spot.key()
                           )
                      )


def deleteSpot(request, spot_key=None):
    models.Spot.get(spot_key).delete()
    return HttpResponseRedirect('/traffic_log/spot')


def spotDetail(request, spot_key=None):
    spot = models.Spot.get(spot_key)
    sys.stderr.write(",".join(str(x) for x in spot.constraints))
    constraints = [forms.SpotConstraintForm(instance=x) for x in spot.constraints]
    form = forms.SpotForm(instance=spot)
    return render('traffic_log/spot_detail.html',
                  {'spot':spot, 'constraints':constraints, 'dow_dict':constants.DOW_DICT}
                  )


def listSpots(request):
    spots = models.Spot.all().order('-created').fetch(20)
    return render('traffic_log/spot_list.html', dict(spots=spots))

def box(thing):
    if isinstance(thing,list):
        return thing
    else:
        return [thing]

def connectConstraintsAndSpot(constraint_keys,spot_key):
    for constraint in map(models.SpotConstraint.get, box(constraint_keys)):
        #sys.stderr.write(",".join(constraint.spots))
        if spot_key not in constraint.spots:
            constraint.spots.append(spot_key)
            constraint.put()

def generateLog(request):
    pass

def traffic_log(request):
    pass


