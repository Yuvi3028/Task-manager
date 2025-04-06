from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    task_name = models.CharField(max_length=255)
    # category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    # assigned_to = models.CharField(max_length=255)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # ForeignKey to User
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(default="09:00")  # Add this field
    end_time = models.TimeField(default="18:00") # Add this field
    estimated_time = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True)  # Hours or minutes
    # time = models.TimeField(null=True, blank=True)
    # target_time = models.CharField(max_length=50, default='10 mins')  # Default value
    # date_assigned = models.DateField(null=True, blank=True)
    def __str__(self):
        return self.task_name
    
class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20)  # 'Login' or 'Logout'
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField(null=True, blank=True)  # In minutes (optional)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    shift_type = models.CharField(max_length=10, choices=[('normal', 'Normal Shift'), ('late', 'Late Shift')], default='normal')
    
    def __str__(self):
        return self.user.username
    
class Shift(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Associate shift with a user
    shift_type = models.CharField(max_length=10, choices=[('normal', 'Normal Shift (09:00 AM - 06:00 PM)'), ('late', 'Late Shift (11:00 AM - 08:00 PM)')])
    date = models.DateField(auto_now_add=True)  # Store the date for the shift

    def __str__(self):
        return f"{self.user.username} - {self.shift_type}"

    @property
    def shift_time_range(self):
        """Returns a readable time range for shift."""
        if self.shift_type == 'normal':
            return "09:00 AM - 06:00 PM"
        elif self.shift_type == 'late':
            return "11:00 AM - 08:00 PM"
        return "Unknown Shift Type"