from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    task_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    assigned_to = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    date_assigned = models.DateField(null=True, blank=True)
    def __str__(self):
        return self.task_name