
"""custom template tags for the volunteers app.

Load this at the top of a template file with the following code::
    
    {% load volunteers_extras %}
    
"""
from django import template
from django.template import resolve_variable
from django.contrib.auth.models import Group

register = template.Library()

@register.filter
def render_claim_task(task, volunteer_index):
    """render a cell for claiming a task within a task table.
    
    example::
        
        <table>
        <tr>
            ...
            <td>{{ task|render_claim_task:0|safe }}</td>
            <td>{{ task|render_claim_task:1|safe }}</td>
            <td>{{ task|render_claim_task:2|safe }}</td>
            ...
        </tr>
        </table>
        
    """
    try:
        volunteer = task.claimed_by[volunteer_index]
    except IndexError:
        zero_based_num_volunteers_needed = task.num_volunteers_needed-1
        if volunteer_index > zero_based_num_volunteers_needed:
            return '<div class="not_needed"></div>'
        else:
            return (
                '<div class="claim_this_task">'
                '<a ch_claim_prompt="%s" href="%s" title="Click to claim this task">'
                'Claim this task</a></div>') % (task.claim_prompt, task.claim_task_url)
    else:
        return '<div class="claimed">%s %s</div>' % (
                        volunteer.first_name, volunteer.last_name)

@register.tag()
def ifusergroup(parser, token):
    """ Check to see if the currently logged in user belongs to a specific
    group. Requires the Django authentication contrib app and middleware.

    Usage: {% ifusergroup Admins %} ... {% endifusergroup %}

    """
    try:
        tag, group = token.split_contents()
    	group.strip("'\"")
    except ValueError:
        raise template.TemplateSyntaxError(
                "Tag 'ifusergroup' requires 1 argument; got: %s." % token.split_contents())
    nodelist = parser.parse(('endifusergroup',))
    parser.delete_first_token()
    return GroupCheckNode(group, nodelist)

class IfGreaterThanNode(template.Node):
    
    def __init__(self, nodelist_for_block, var1, var2, number_literal, greater_than_literal):
        self.nodelist_for_block = nodelist_for_block
        self.var1, self.var2 = template.Variable(var1), template.Variable(var2)
        self.number_literal = number_literal
        self.greater_than_literal = greater_than_literal

    def __repr__(self):
        return "<IfGreaterThanNode>"

    def render(self, context):
        try:
            number = self.var1.resolve(context)
        except template.VariableDoesNotExist:
            number = int(self.number_literal)
        try:
            greater_than = self.var2.resolve(context)
        except template.VariableDoesNotExist:
            greater_than = int(self.greater_than_literal)
        
        if number > greater_than:
            return self.nodelist_for_block.render(context)
        else:
            return ''
        
@register.tag()
def ifgreaterthan(parser, token):
    try:
        tag, number, greater_than = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
                "Tag 'ifgreaterthan' requires 2 arguments; got: %s." % token.split_contents())
                
    end_tag = 'end' + tag
    nodelist_for_block = parser.parse((end_tag,))
    parser.delete_first_token()
        
    return IfGreaterThanNode(nodelist_for_block, number, greater_than, number, greater_than)

class GroupCheckNode(template.Node):
    
    def __init__(self, group, nodelist):
        if group[0] in ["'", '"'] :
            self.group = group[1:-1]
        else :
            self.group = group
        self.nodelist = nodelist
        
    def render(self, context):
        user = resolve_variable('user', context)
        if not user.is_authenticated:
            return ''
        try:
            group = Group.objects.get(name=self.group)
        except Group.DoesNotExist:
            return ''
        if group in user.groups.all():
            return self.nodelist.render(context)
        return ''
