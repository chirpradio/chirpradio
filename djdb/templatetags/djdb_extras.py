"""custom template tags for the djdb app.

Load this at the top of a template file with the following code::
    
    {% load djdb_extras %}
    
"""
from django import template
from django.template import resolve_variable
from django.template import Node, NodeList, Template, Context, Variable
from django.template import TemplateSyntaxError, VariableDoesNotExist
from djdb.models import User, Crate

register = template.Library()

@register.tag
def ifincrate(parser, token):
    """
    Renders the block if item is in a crate.
    """
    bits = token.contents.split()
    if len(bits) != 3:
        raise TemplateSyntaxError(
                "ifincrate requires two arguments, the user and the item")
    nodelist_true = parser.parse(('else', 'endifincrate'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endifincrate',))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    return IfInCrate(nodelist_true, nodelist_false, bits[1], bits[2])

class IfInCrate(Node):
    def __init__(self, nodelist_true, nodelist_false, user, item):
        self.user = Variable(user)
        self.item = Variable(item)
        
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false

    def render(self, context):
        user = self.user.resolve(context)
        item = self.item.resolve(context)

        crate = Crate.all().filter("user =", user).fetch(1)
        if len(crate) == 0:
            return self.nodelist_false.render(context)
        else:
            if item.key() in crate[0].items:
                return self.nodelist_true.render(context)
            else:
                return self.nodelist_false.render(context)
