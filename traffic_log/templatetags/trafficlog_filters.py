from django import template
register = template.Library()

@register.filter
def hash(h, key):
    return h[key]

@register.filter
def dd(value):
    value = int(value)
    return value if value >=10 else "0%d"%value
    
