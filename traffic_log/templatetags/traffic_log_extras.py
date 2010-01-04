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

"""custom template tags for the traffic_log app.

Load this at the top of a template file with the following code::
    
    {% load traffic_log_extras %}
    
"""
from django import template
from django.template import resolve_variable
from django.template import Node, NodeList, Template, Context, Variable
from django.template import TemplateSyntaxError, VariableDoesNotExist

register = template.Library()

@register.tag
def url_to_finish_spot(parser, token):
    """gets the URL to finish this spot at the given constraint."""
    args = token.split_contents()
    if len(args) != 3:
        raise TemplateSyntaxError(
            "url_to_finish_spot requires a spot_constraint and spot as argument")
    node = URLToFinishNode(args[1:])
    return node

class URLToFinishNode(Node):
    
    def __init__(self, vars):
        vars = [Variable(v) for v in vars]
        self.constraint_var, self.spot_var = vars

    def render(self, context):
        constraint = self.constraint_var.resolve(context)
        spot = self.spot_var.resolve(context)
        return constraint.url_to_finish_spot(spot)

