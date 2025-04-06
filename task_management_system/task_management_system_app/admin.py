from django.contrib import admin
from .models import Category, Task, UserActivity


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_name',  'assigned_to','start_date', 'end_date', 'estimated_time')
    # list_filter = ('category',)
    search_fields = ('name', )

class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'formatted_timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username',)

    def formatted_timestamp(self, obj):
        """Format the timestamp to a more readable format (e.g., '2025-03-12 09:37')."""
        return obj.timestamp.strftime('%Y-%m-%d %H:%M')
    formatted_timestamp.admin_order_field = 'timestamp'  # Allow sorting by timestamp
    formatted_timestamp.short_description = 'Timestamp'  # Custom column name in admin

admin.site.register(UserActivity, UserActivityAdmin)

