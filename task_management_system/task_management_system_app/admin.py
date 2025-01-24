from django.contrib import admin
from .models import Category, Task


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_name',  'assigned_to','start_date', 'end_date','date_assigned')
    # list_filter = ('category',)
    search_fields = ('name', )

    

