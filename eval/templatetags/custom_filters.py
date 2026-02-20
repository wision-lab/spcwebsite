from django import template

register = template.Library()


@register.filter
def na_if_missing(value, float_places=3):
    """
    Returns 'N/A' if value is -1 or None, otherwise formats the value to the specified
    number of decimal places.
    """
    if value in ("null", "none", "None", None):
        return "N/A"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    if value == -1:
        return "N/A"
    return f"{value:.{int(float_places)}f}"


@register.filter(name="zip")
def zip_lists(a, b):
    return zip(a, b)
