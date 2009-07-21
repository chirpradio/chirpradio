
"""custom template tags for the playlists app.

Load this at the top of a template file with the following code::
    
    {% load playlists_extras %}
    
"""
from django import template
from django.template import resolve_variable
from django.template import Node, NodeList, Template, Context, Variable
from django.template import TemplateSyntaxError, VariableDoesNotExist
from playlists.models import PlaylistBreak, PlaylistTrack

register = template.Library()

@register.tag
def ifeventisbreak(parser, token):
    """
    Renders the block if PlaylistEvent object is a break.        
    """
    bits = token.contents.split()
    nodelist_true = parser.parse(('else', 'endifeventisbreak'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endifeventisbreak',))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    if len(bits) != 2:
        raise TemplateSyntaxError(
                "ifeventisbreak requires a single argument, "
                "the PlaylistEvent() instance")
    return IfEventIsBreakNode(nodelist_true, nodelist_false, bits[1])

class IfEventIsBreakNode(Node):
    def __init__(self, nodelist_true, nodelist_false, var1):
        self.var1 = Variable(var1)
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false

    def render(self, context):
        try:
            val1 = self.var1.resolve(context)
        except VariableDoesNotExist:
            val1 = None
        
        if type(val1) == PlaylistBreak:
            return self.nodelist_true.render(context)
        else:
            return self.nodelist_false.render(context)
