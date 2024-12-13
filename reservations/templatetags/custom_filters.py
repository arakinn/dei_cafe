from django import template

register = template.Library()

@register.filter
def get_item(form, item_id):
    return form[f'item_{item_id}']

@register.filter
def multiply(value, arg):
    try:
        return value * arg
    except (ValueError, TypeError):
        return ''