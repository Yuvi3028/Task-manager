# task_management_system_app/templatetags/signals.py
from django import template
from task_management_system_app.models import UserProfile

register = template.Library()

# Example template tag
@register.filter(name='shift_type')
def get_shift_type(user):
    try:
        return user.profile.shift_type
    except UserProfile.DoesNotExist:
        return 'Unknown Shift'