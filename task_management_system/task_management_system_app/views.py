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
import openpyxl
import pandas as pd




BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def is_admin(user):
    return user.is_superuser


admin_required = user_passes_test(lambda user: user.is_superuser)

# @login_required
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
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']


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
            # login(request, user)
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'task_management_system_app/register.html', {'form': form})


# def user_profile(request):
#     return render(request, 'profile.html')

def LogoutPage(request):
    logout(request)
    return redirect("login")


@login_required
@admin_required
def delete_task(request, task_id):
    if request.method == 'POST':
        task = Task.objects.get(id=task_id)
        task.delete()
    return redirect(reverse('category_list'))

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
def update_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)  # Get the task by its ID
    users = User.objects.all()
    if request.method == 'POST':
        form = TaskForm(request.POST)  # Pre-populate the form with the existing task data
        if form.is_valid():
                # Get the user by username from the form data
                assigned_user = User.objects.get(username=form.cleaned_data['assigned_to'])

                # Create and save the task in the database
                task = form.save(commit=False)  # Create the task but don't save it yet
                task.assigned_to = assigned_user  # Set assigned user manually
                task.save()  # Now save the task

                # Show success message and redirect to the home page
                messages.success(request, 'Task has been successfully created!')
                return redirect('view_task_list')# Redirect back to the home page or a list of tasks
        else:
            # If the form is not valid, print the errors for debugging
            messages.error(request, 'Form submission error. Please check the input data.')
    else:
        form = TaskForm()  # Initialize the form with the existing task data
    
    return render(request, 'task_management_system_app/update_task.html', {'form': form, 'task': task, 'user': users})


@login_required
@admin_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)  # Get the task by ID

    if request.method == 'POST':  # Confirm deletion by POST request
        task.delete()  # Delete the task
        messages.success(request, 'Task deleted successfully!')

        # Capture the date range from the request GET parameters
        from_date = request.GET.get('from_date', None)
        to_date = request.GET.get('to_date', None)

        # Check if the request is an AJAX request and respond accordingly
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})  # Return a JSON response for AJAX

        # Redirect back to the task list with the same date range
        if from_date and to_date:
            return redirect(f'{request.path}?from_date={from_date}&to_date={to_date}')

        # If no date range is provided, redirect to the general task list page
        return redirect('view_task_list')

    # If not a POST request, return an error
    return JsonResponse({'error': 'Invalid request method'}, status=400)

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

    if request.user.is_superuser:
        # Admins can see all tasks
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
        # Regular users can see their own tasks only
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

    return render(request, 'view_task_list.html', {'tasks': tasks, 'from_date': from_date, 'to_date': to_date})


@login_required
@admin_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'task_management_system_app/category_list.html', {'categories': categories})


@login_required
@admin_required
def create_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('category_list')  # Replace with your desired redirect
    else:
        form = CategoryForm()
    return render(request, 'create_category.html', {'form': form})

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

def create_category_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')  # Redirect to a success page or another view
    else:
        form = CategoryForm()
    return render(request, 'create_category.html', {'form': form})

@login_required
@admin_required
def delete_category(request, category_id):
    category = Category.objects.get(pk=category_id)
    if category.task_set.exists():
        messages.error(
            request, "You cannot delete this category as it contains tasks.")
    else:
        category.delete()
        messages.success(request, "Category deleted successfully.")
    return redirect('category_list')


@login_required
@admin_required
def category_tasks(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    tasks = category.task_set.all()
    return render(request, 'task_management_system_app/category_tasks.html', {'category': category, 'tasks': tasks})


# @login_required
# @admin_required
def task_chart(request):
    categories = Category.objects.all()
    users = User.objects.all()

    # Count pending tasks by category
    pending_counts_by_category = {}
    for category in categories:
        pending_counts_by_category[category.name] = Task.objects.filter(
            category=category,
            start_date__gt=timezone.now()  # Pending tasks (not started yet)
        ).count()

    # Count pending tasks by user
    pending_counts_by_user = {}
    for user in users:
        pending_counts_by_user[user.username] = Task.objects.filter(
            assigned_to=user,
            start_date__gt=timezone.now()  # Pending tasks (not started yet)
        ).count()

    return render(
        request,
        'task_management_system_app/task_chart.html',
        {
            'pending_counts_by_category': pending_counts_by_category,
            'pending_counts_by_user': pending_counts_by_user,
        }
    )