
""" common custom template tags.

Load this at the top of a template file with the following code::
    
    {% load common_extras %}
    
"""
from django import template
from django.template.defaultfilters import stringfilter
import re

register = template.Library()

@register.filter
@stringfilter
def replace(string, args):
    """
    Perform a regular expression search and replace.
    
    Usage: {{ var|replace:"/search/replace" }}
    """
    search = args.split(args[0])[1]
    replace = args.split(args[0])[2]
    return re.sub(search, replace, string)
