from django import template

register = template.Library()

@register.filter
def get_item(form, item_id):
    """フォームフィールドを動的に取得"""
    return form[f'item_{item_id}']