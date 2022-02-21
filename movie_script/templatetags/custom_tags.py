from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='orderDict')
def orderDict(value, key):
    """
        Returns the value turned into a list.
    """
    result = value.split(key)
    result = {k: v for k, v in enumerate(result, 1)}

    return result

@register.filter(name='dict_key')
def dict_key(d, k):
    '''Returns the given key from a dictionary.'''
    return d[k]

@register.filter(name='get_dict')
def get_dict(dictionary, key):
    return dictionary.get(key)

@register.filter
@stringfilter
def add_braces(value):
    return "["+value+"]"

def update_variable(value):
    data = value
    return data

register.filter('update_variable', update_variable)

from django import template
register = template.Library()

@register.filter
def index(indexable, i):
    return indexable[i]

@register.filter
def get_at_index(object_list, index):
    return object_list[index]