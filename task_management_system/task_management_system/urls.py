"""
URL configuration for task_assigner project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from task_management_system_app import views
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', views.user_tasks_list, name='user_tasks_list'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', views.register, name='register'),
    path('home/', views.home, name='home'),
    path('download_tasks/', views.download_tasks, name='download_tasks'),
    path('login/', views.user_login, name='login'),
    path("logout/", views.LogoutPage, name="logout"),
    # path('', views.category_list, name='category_list'),
    # path('categories/create/', views.create_category, name='create_category'),
    # path('categories/<int:category_id>/', views.category_tasks, name='category_tasks'),
    # path('categories/delete/<int:category_id>/', views.delete_category, name='delete_category'),
    path('tasks/create/', views.create_task, name='create_task'),
    path('create_daily/', views.create_daily_task, name='create_daily_task'),
    path('tasks/update/<int:task_id>/', views.update_task, name='update_task'),
    path('tasks/delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('task/<int:task_id>/edit/', views.update_task, name='update_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('task-list/', views.view_task_list, name='view_task_list'),
    path('task-chart/', views.task_chart, name='task_chart'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    # path('profile/', views.user_profile, name='profile'),
   
]

