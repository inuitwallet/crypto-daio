from django.template.defaultfilters import stringfilter
from django.template.defaulttags import register


@register.filter
@stringfilter
def human_time(num_minutes):
    print(num_minutes)
    num_minutes = int(num_minutes)

    if num_minutes < 60:
        # less than 1 hour so return minutes
        value = num_minutes
        unit = 'minutes' if value == 1 else 'minutes'
        return '{} {}'.format(value, unit)

    if num_minutes < 1440:
        # less than 1 day
        # return number of hours
        value = num_minutes / 60
        unit = 'hour' if value == 1 else 'hours'
        return '{} {}'.format(value, unit)

    # return number of days
    value = int((num_minutes / 60) / 24)
    unit = 'day' if value == 1 else 'days'
    return '{} {}'.format(value, unit)
