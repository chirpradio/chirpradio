from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.conf import settings
from django.template import Context, loader
from django.utils import simplejson

from traffic_log import models, forms, constants

def render(template, payload):
    return render_to_response(template, payload)

def index(request):
    spots = models.Spot.all().order('-created').fetch(20)
    return render('traffic_log/index.html', dict(spots=spots))


def createSpotConstraint(request):
    constraints = []
    if request.method=='POST':
        constraint_form = forms.SpotConstraintForm(request.POST)
        if constraint_form.is_valid():
            constraint = constraint_form.cleaned_data
            dows = [ int(x) for x in constraint['dow_list'] ]

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
                    constraints.append(forms.SpotConstraintForm(instance=obj))
                    
            return HttpResponseRedirect('/traffic_log/spot_constraint/')
    else:
        constraints = [forms.SpotConstraintForm()]
        
    return render('traffic_log/create_edit_spot_constraint.html',{'constraints':constraints})


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

    else:

        return render('traffic_log/create_edit_spot_constraint.html', 
                      dict(constraints=[forms.SpotConstraintForm(instance=constraint)],
                           edit=True,
                           formaction="/traffic_log/spot_constraint/edit/%s"%constraint.key()
                           )
                      )



def deleteSpotConstraint(request, spot_constraint_key=None):
    models.SpotConstraint.get(spot_constraint_key).delete()
    return HttpResponseRedirect('/traffic_log/spot_constraint/')

def addSpotToConstraint(request, spot_constraint_key, spot_key=None):
    pass

def assignSpotConstraint(request, spot_key=None, spot_constraint_key=None):
    pass

def listSpotConstraints(request):
    constraints = models.SpotConstraint.all().order('dow').order('hour').order('slot')
    return render('traffic_log/view_constraints.html', {'constraints':constraints, 'dow_dict':constants.DOW_DICT})


def createSpot(request):

    if request.method == 'POST':
        spot_form = forms.SpotForm(request.POST)

        if spot_form.is_valid():
            spot = spot_form.save()
        return HttpResponseRedirect('/traffic_log/spot/')
    else:
        spot_form = forms.SpotForm()

    return render('traffic_log/create_edit_spot.html', 
                  dict(spot=spot_form,formaction="/traffic_log/spot/create/")
                  )


def spotDetail(request, spot_key=None):
    spot = models.Spot.get(spot_key)
    form = forms.SpotForm(instance=spot)
    return render('traffic_log/spot_detail.html',{'spot':spot, 'dow_dict':constants.DOW_DICT} )


def editSpot(request, spot_key=None):
    spot = models.Spot.get(spot_key)

    if request.method ==  'POST':
        spot_form = forms.SpotForm(request.POST)

        if spot_form.is_valid():
            for field in spot_form.fields.keys():
                setattr(spot,field,spot_form.cleaned_data[field])
                
                models.Spot.put(spot)

        return HttpResponseRedirect('/traffic_log/spot/')

    else:
        return render('traffic_log/create_edit_spot.html', 
                      dict(spot=forms.SpotForm(instance=spot),
                           edit=True,
                           formaction="/traffic_log/spot/edit/%s"%spot.key()
                           )
                      )


def deleteSpot(request, spot_key=None):
    models.Spot.get(spot_key).delete()
    return HttpResponseRedirect('/traffic_log/spot')


def listSpots(request):
    spots = models.Spot.all().order('-created').fetch(20)
    return render('traffic_log/spot_list.html', dict(spots=spots))


def connectConstraintAndSpot(constraint_key,spot_key):
    constraint = models.SpotConstraint.get(constraint_key)
    if spot_key not in constraint.spots:
        constraint.spots.append(spot_key)

def generateLog(request):
    pass

def traffic_log(request):
    pass


