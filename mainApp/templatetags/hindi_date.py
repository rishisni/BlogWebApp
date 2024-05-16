import babel.dates
from django import template

register = template.Library()

@register.filter
def hindi_date(value, date_format="d MMMM, YYYY"):
    try:
        return babel.dates.format_date(value, date_format, locale='hi_IN')
    except (ValueError, TypeError):
        return value
