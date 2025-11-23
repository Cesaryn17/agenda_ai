from django import template

register = template.Library()

@register.filter
def primeiro(value):
    if isinstance(value, str) and len(value) > 0:
        return value[0]
    return ''

@register.filter
def maiusculo(value):
    if isinstance(value, str):
        return value.upper()
    return value