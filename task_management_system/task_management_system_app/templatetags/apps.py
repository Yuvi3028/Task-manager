# task_management_system_app/apps.py

from django.apps import AppConfig

class TaskManagementSystemAppConfig(AppConfig):
    name = 'task_management_system_app'

    def ready(self):
        import task_management_system_app.signals
