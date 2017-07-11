from django.template.defaultfilters import stringfilter
from django.template.defaulttags import register


@register.filter
@stringfilter
def human_time(num_minutes):
    print(num_minutes)
    num_minutes = int(num_minutes)

    if num_minutes < 1440:
        # less than 1 day
        # return number of hours
        return '{} hours'.format(int(num_minutes / 60))

    else:
        return '{} days'.format(int((num_minutes / 60) / 24))
