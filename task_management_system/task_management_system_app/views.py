from django.contrib.auth import login, logout
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Category, Task
from .forms import CategoryForm,TaskForm,forms
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import is_aware, make_naive
from django.views.decorators.csrf import csrf_exempt
from dateutil import parser
import datetime
from datetime import datetime
import pandas as pd
from django.http import HttpResponse
from django.db import transaction
from .forms import TaskForm
import json
import random
import os
import re
import openpyxl
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def is_admin(user):
    return user.is_superuser

admin_required = user_passes_test(lambda user: user.is_superuser)

#@login_required
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_superuser:
                # Redirect admin users to admin dashboard
                return redirect('home')
            else:
                # Redirect regular users to their home page
                return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


# @login_required
@login_required
def user_tasks_list(request):
    tasks = Task.objects.filter(assigned_to=request.user)
    return render(request, 'task_management_system_app/user_tasks_list.html', {'tasks': tasks})



class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)  # Add this line for email field

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class LoginForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ['username', 'password']
        
    
@login_required
def home(request):
    # Get today's date
    today = datetime.today().date()
    users = User.objects.exclude(username='admin')  # Exclude admin user from regular users

    # Get the selected users from the GET parameters (for admin only)
    selected_users = request.GET.getlist('selected_users')  # List of selected users (array of usernames)

    # Initialize from_date and to_date as None by default
    from_date = request.GET.get('from_date', None)
    to_date = request.GET.get('to_date', None)

    tasks = Task.objects.all()  # Default to all tasks initially

    # Handle date range filter if provided in the GET request
    if from_date and to_date:
        try:
            # Parse the from_date and to_date from the GET request
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()

            # Filter tasks based on the date range
            tasks = tasks.filter(start_date__gte=from_date, end_date__lte=to_date)
        except ValueError:
            pass  # Handle invalid date format gracefully
        
    # Display login success message only once
    if not request.session.get('has_logged_in', False):  # Check if the user has logged in before
        messages.success(request, "Login Successfully!")  # Set message
        request.session['has_logged_in'] = True  # Set flag to True

    # Admin view: show tasks for all users and allow user selection for filtering tasks
    if request.user.is_superuser:
        task_counts = {}
        task_names = {}

        # If no date range is selected (i.e., from_date and to_date are None), filter for today's tasks
        if not from_date and not to_date:
            tasks = Task.objects.filter(start_date__lte=today, end_date__gte=today)

        # Fetch tasks assigned to each user (considering the date filters)
        for user in users:
            # Exclude the admin user from the chart
            if user.is_superuser:
                continue

            user_tasks = tasks.filter(assigned_to=user)
            task_counts[user.username] = user_tasks.count()
            task_names[user.username] = [task.task_name for task in user_tasks]

        # Prepare the data for the chart
        user_names = list(task_counts.keys())
        task_counts_values = list(task_counts.values())
        task_names_values = list(task_names.values())

        # Store selected users in session
        if selected_users:
            request.session['selected_users'] = selected_users    
            
        # Render the template with task distribution chart data, filtered tasks, and selected users
        return render(request, 'home.html', {
            'user_names': json.dumps(user_names),
            'task_counts_values': json.dumps(task_counts_values),
            'task_names_values': json.dumps(task_names_values),
            'tasks': tasks,  # Pass the filtered tasks to the template
            'from_date': from_date,
            'to_date': to_date,
            'users': users,
            'selected_users': selected_users,  # Pass selected users to the template for admin
        })
    
    # For regular users: filter tasks for the logged-in user and the selected date range
    else:
        # Regular users only see their own tasks, no user selection dropdown
        tasks = tasks.filter(assigned_to=request.user)

        # Apply date range filters if provided
        if from_date and to_date:
            tasks = tasks.filter(start_date__gte=from_date, end_date__lte=to_date)
        else:
            # Default to today's tasks if no date range is provided
            tasks = tasks.filter(start_date__lte=today, end_date__gte=today)
        tasks = sorted(tasks, key=lambda task: extract_time_from_task_name(task.task_name) or datetime.min)
        # Render the template with tasks assigned to the logged-in user and filter parameters
        return render(request, 'home.html', {
            'tasks': tasks,
            'from_date': from_date,
            'to_date': to_date,
            'users': users,
            'selected_users': selected_users,  # Pass selected users here for the admin view
        })
        
# Add a view for downloading tasks in Excel format
@login_required
def download_tasks(request):
    from_date = request.GET.get('start_date', None)
    to_date = request.GET.get('end_date', None)
    
    # Fetch tasks, filtered by the date range if provided
    tasks = Task.objects.all()
    
    if from_date and to_date:
        tasks = tasks.filter(start_date__gte=from_date, end_date__lte=to_date)

    # Sort tasks by start_date in ascending order
    tasks = tasks.order_by('start_date')
    
    # Get the current user if logged in (assuming you're generating the report for a specific user)
    user = request.user
    if not user.is_superuser:  # If not admin, filter by logged-in user
        tasks = tasks.filter(assigned_to=user)
    
    # Convert tasks to DataFrame
    tasks_data = {
        'Task Name': [task.task_name for task in tasks],
        'Assigned To': [task.assigned_to for task in tasks],
        # 'Category': [task.category for task in tasks],
        'Start Date': [task.start_date.replace(tzinfo=None) if isinstance(task.start_date, datetime) and is_aware(task.start_date) else task.start_date for task in tasks],  # Make datetime timezone unaware
        'End Date': [task.end_date.replace(tzinfo=None) if isinstance(task.end_date, datetime) and is_aware(task.end_date) else task.end_date for task in tasks],  # Make datetime timezone unaware
    }

    df = pd.DataFrame(tasks_data)

    # Generate a dynamic file name based on the assigned user's username and today's date
    file_name = f"{user.username}_{datetime.now().strftime('%d-%m-%Y')}_tasks.xlsx"

    # Create HTTP response with Excel file content
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    # Write the data to the Excel file
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    return response

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data.get('email')  # Save the email to the user instance
            user.save()  # Don't forget to save the user instance with the email
            # login(request, user)  # You can log in the user if you want
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'task_management_system_app/register.html', {'form': form})

def LogoutPage(request):
    logout(request)
    # if not request.session.get('has_logged_in', False):  # Check if the user has logged in before
    #         messages.success(request, "Login Successfully!")  # Set message
    #         request.session['has_logged_in'] = True  # Set flag to True
    messages.success(request, "Logout Successfully!")
    return redirect("login")

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_name', 'category', 'assigned_to', 'start_date', 'end_date']

    task_name = forms.CharField(max_length=255)
    category = forms.CharField(max_length=255)
    assigned_to = forms.CharField(max_length=255)
    start_date = forms.DateField()
    end_date = forms.DateField()
    
class TaskForm(forms.Form):
    
    class Meta:
        model = Task
        fields = ['task_name', 'category', 'assigned_to', 'start_date', 'end_date']
    task_name = forms.CharField(max_length=100)
    assigned_to = forms.CharField(max_length=100)
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    category = forms.CharField(max_length=100) 

def load_tasks_from_excel(file_path):
    try:
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            return df['Task Name'].dropna().tolist()  # List of task names from the Excel file
        return []
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        return []

def assign_tasks(request, tasks, users_list, success_message, is_daily_task=False):
    # Handle task creation when form is submitted
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        new_task_name = request.POST.get('new_task_name')  # New task entered by the user
        assigned_to = request.POST.get('assigned_to')  # User selected for the task

        # Validate the dates
        if not start_date or not end_date:
            messages.error(request, 'Please select both start and end dates.')
            return redirect('create_daily_task' if is_daily_task else 'create_task')

        # Case 1: If new task name and assigned user are provided, create the task manually
        if new_task_name and assigned_to:
            try:
                assigned_user = User.objects.get(username=assigned_to)  # Get the selected user from DB
                # Create and save the new task
                Task.objects.create(
                    task_name=new_task_name,
                    assigned_to=assigned_user,
                    start_date=start_date,
                    end_date=end_date
                )
                messages.success(request, f"Task '{new_task_name}' has been created and assigned to {assigned_to}.")
                return redirect('create_daily_task' if is_daily_task else 'create_task')

            except User.DoesNotExist:
                messages.error(request, 'The selected user does not exist.')
                return redirect('create_daily_task' if is_daily_task else 'create_task')

        # Case 2: If no new task is entered, proceed to automatic task assignment from the Excel or predefined tasks
        elif tasks and users_list:
            # Shuffle the list of tasks to randomize the order
            random.shuffle(tasks)

            # Shuffle selected users as well (if needed)
            random.shuffle(users_list)

            # Track assignments to ensure each task is assigned to a user
            task_assignments = []

            # Assign tasks to users in a random order
            for i, task_name in enumerate(tasks):
                assigned_user = users_list[i % len(users_list)]  # Assign to a user randomly
                # Create the task for the user
                Task.objects.create(
                    task_name=task_name,
                    assigned_to=assigned_user,
                    start_date=start_date,
                    end_date=end_date
                )
                task_assignments.append(task_name)

            messages.success(request, f'{len(task_assignments)} tasks have been automatically assigned to users successfully!')
            return redirect('create_daily_task' if is_daily_task else 'create_task')

        else:
            messages.error(request, 'No tasks or users found to assign tasks to.')

    # Rendering directly with hard-coded templates
    return render(request, 'task_management_system_app/create_daily_task.html' if is_daily_task else 'task_management_system_app/create_task.html', {'users': users_list, 'tasks': tasks})

@login_required
def create_task(request):
    excel_file_path = "tasks.xlsx"
    tasks = load_tasks_from_excel(excel_file_path)

    # Get selected users from the session (store the selected users in session in the home view)
    selected_users_usernames = request.session.get('selected_users', [])
    
    # Fetch users from the database, excluding the admin user, and filter by selected usernames
    users = User.objects.filter(username__in=selected_users_usernames)
    users_list = list(users)

    # Call helper function to handle task creation
    return assign_tasks(request, tasks, users_list, 'create_task', is_daily_task=False)

@login_required
def create_daily_task(request):
    excel_file_path = "tasks1.xlsx"
    tasks = load_tasks_from_excel(excel_file_path)

    # Get selected users from the session (store the selected users in session in the home view)
    selected_users_usernames = request.session.get('selected_users', [])
    
    # Fetch users from the database, excluding the admin user, and filter by selected usernames
    users = User.objects.filter(username__in=selected_users_usernames)
    users_list = list(users)

    # Call helper function to handle task creation
    return assign_tasks(request, tasks, users_list, 'create_daily_task', is_daily_task=True)

@login_required
@admin_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)  # Get the task by ID

    if request.method == 'POST':  # Confirm deletion by POST request
        # task_name = task.task_name  # Save task name to display in the success message
        task.delete()  # Delete the task
        messages.success(request, f"Task deleted successfully!")

        # Capture the date range from the request GET parameters
        from_date = request.GET.get('from_date', None)
        to_date = request.GET.get('to_date', None)

        # Check if the request is an AJAX request and respond accordingly
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})  # Return a JSON response for AJAX

        # Redirect back to the task list with the same date range (if provided)
        if from_date and to_date:
            return redirect(f'/task-list/?from_date={from_date}&to_date={to_date}')

        # If no date range is provided, redirect to the general task list page
        return redirect('view_task_list')

    # If not a POST request, return an error
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
@admin_required
def delete_selected_tasks(request):
    if request.method == 'POST':
        # Get selected task IDs from the POST data
        task_ids = request.POST.getlist('tasks_to_delete')
        
        if task_ids:
            # Try to get all tasks that match the selected IDs
            tasks = Task.objects.filter(id__in=task_ids)
            
            # Delete the tasks
            tasks.delete()
            
            messages.success(request, f"Selected tasks deleted successfully!")
        else:
            messages.error(request, "No tasks selected for deletion.")
        
        # Redirect back to the task list page
        return redirect('view_task_list')
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)

from datetime import datetime

# Function to extract time from task name (like '5:30 PM EST' from the task names)
from datetime import datetime

# Function to extract time from task name (like '4:30 PM' from the task names)
def extract_time_from_task_name(task_name):
    try:
        # Find the last occurrence of a time in the format of 'HH:MM AM/PM'
        parts = task_name.split(' ')
        
        # Check if the last three parts contain the time (e.g., '4:30 PM')
        time_str = None
        if len(parts) >= 4:
            time_str = parts[-4] + ' ' + parts[-3]  # This gives us the time part (e.g., '4:30 PM')
        
        # If the time_str is found, convert it to a datetime object
        if time_str:
            return datetime.strptime(time_str, '%I:%M %p')  # Convert to datetime object

        return None  # If time extraction fails, return None
    except Exception as e:
        # print(f"Error extracting time from task name: {task_name}, error: {e}")
        return None  # Return None if there is an error

@login_required
@admin_required
def view_task_list(request):
    # Get the 'from_date' and 'to_date' from the GET request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Get the current date to filter tasks by today's date
    today = datetime.today().date()

    # Filter tasks for the logged-in user (for regular users)
    tasks = Task.objects.all()

    # Get selected users from the session (store the selected users in session in the home view)
    selected_users_usernames = request.session.get('selected_users', [])
    
    # Get the list of users based on session or return all users
    if selected_users_usernames:
        users = User.objects.filter(username__in=selected_users_usernames)
    else:
        users = User.objects.filter(is_superuser=False)  # Exclude admin users
    
    users_list = list(users)
    
    # Admins can see all tasks, regular users can see their own tasks
    if request.user.is_superuser:
        # Admin can see all tasks and filter by dates
        if from_date:
            try:
                from_date = parser.parse(from_date).date()  # Use dateutil.parser to handle flexible formats
                tasks = tasks.filter(start_date__gte=from_date)
            except ValueError:
                messages.error(request, f"Invalid 'from_date' format: {from_date}")

        if to_date:
            try:
                to_date = parser.parse(to_date).date()  # Use dateutil.parser to handle flexible formats
                tasks = tasks.filter(end_date__lte=to_date)
            except ValueError:
                messages.error(request, f"Invalid 'to_date' format: {to_date}")
            
        else:
            # Default to today's date if no date filter is provided
            tasks = tasks.filter(start_date__lte=today, end_date__gte=today)
    else:
        # Regular users can see only their own tasks
        tasks = tasks.filter(assigned_to=request.user)

        if from_date:
            try:
                from_date = parser.parse(from_date).date()  # Use dateutil.parser to handle flexible formats
                tasks = tasks.filter(start_date__gte=from_date)
            except ValueError:
                messages.error(request, f"Invalid 'from_date' format: {from_date}")

        if to_date:
            try:
                to_date = parser.parse(to_date).date()  # Use dateutil.parser to handle flexible formats
                tasks = tasks.filter(end_date__lte=to_date)
            except ValueError:
                messages.error(request, f"Invalid 'to_date' format: {to_date}")
        else:
            # Default to today's date if no date filter is provided
            tasks = tasks.filter(start_date__lte=today, end_date__gte=today)

    # Sort tasks by time extracted from the task name
    tasks = sorted(tasks, key=lambda task: extract_time_from_task_name(task.task_name) or datetime.min)
    
    # Pass the full list of users and filtered tasks to the template
    return render(request, 'view_task_list.html', {
        'tasks': tasks,
        'from_date': from_date,
        'to_date': to_date,
        'users_list': users_list,  # Pass the list of users to the template for dropdown
    })

# @csrf_exempt  # If using AJAX, we may need to disable CSRF protection, but only for AJAX
def change_assigned_user(request, task_id):
    # Get the task based on task_id
    task = get_object_or_404(Task, id=task_id)
    
    # Get the new assigned user from the form data
    assigned_to_username = request.POST.get('assigned_to')
    
    # Get the user object associated with the selected username
    assigned_to_user = User.objects.filter(username=assigned_to_username).first()
    
    if assigned_to_user:
        # Update the task's assigned user
        task.assigned_to = assigned_to_user
        task.save()
        
        messages.success(request, f"Task assigned to {assigned_to_user.username} successfully.")
    else:
        messages.error(request, "Invalid user selected.")
    
    # Redirect back to the task list view
    return redirect('view_task_list')

def forgot_password(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            # Sends password reset email
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name="registration/password_reset_email.html",
            )
            messages.success(
                request, "Password reset email has been sent. Please check your inbox."
            )
            return redirect("login")
        else:
            messages.error(request, "Please enter a valid email address.")
    else:
        form = PasswordResetForm()

    context = {"form": form}
    return render(request, "task_management_system_app/forgot_password.html", context)

