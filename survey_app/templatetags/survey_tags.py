"""
Custom template tags and filters for the survey app.
"""
from django import template
import json

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def get_index(lst, index):
    """
    Get an item from a list by index.
    Usage: {{ mylist|get_index:0 }}
    """
    if lst is None:
        return None
    try:
        index = int(index)
        if isinstance(lst, (list, tuple)) and 0 <= index < len(lst):
            return lst[index]
    except (ValueError, TypeError):
        pass
    return None


@register.filter
def to_json(value):
    """
    Convert a Python object to JSON string.
    Usage: {{ mydict|to_json }}
    """
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return '{}'


@register.filter
def getattr_filter(obj, attr):
    """
    Get an attribute from an object.
    Usage: {{ obj|getattr_filter:'attribute_name' }}
    """
    if obj is None:
        return None
    return getattr(obj, attr, None)
