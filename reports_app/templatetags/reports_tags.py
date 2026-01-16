"""Template tags for reports_app."""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    if dictionary is None:
        return {}
    return dictionary.get(key, {})


@register.filter
def get_attr(obj, attr):
    """Get an attribute from an object."""
    return getattr(obj, attr, None)


@register.simple_tag
def make_review_key(category, subcategory, index):
    """Build a review lookup key from category, subcategory, and index."""
    return f"{category}|{subcategory}|{index}"
