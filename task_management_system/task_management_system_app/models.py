from django.db import models
from django.contrib.auth.models import User

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
    estimated_time = models.DurationField(null=True, blank=True)
    # time = models.TimeField(null=True, blank=True)
    # target_time = models.CharField(max_length=50, default='10 mins')  # Default value
    # date_assigned = models.DateField(null=True, blank=True)
    def __str__(self):
        return self.task_name