from django.contrib.auth import login, logout
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib import messages
from .models import Task
from .forms import forms
from django.dispatch import receiver
from django.utils import timezone
from .models import UserActivity
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordResetForm
from django.utils import timezone
from django.utils.timezone import is_aware
from dateutil import parser
from datetime import datetime
import pandas as pd
from django.http import HttpResponse
import json
import random
import os


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
    email = forms.EmailField(required=False)  # Add this line for email field

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class LoginForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ['username', 'password']

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        activity_type='Login',
        timestamp=timezone.now()
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    UserActivity.objects.create(
        user=user,
        activity_type='Logout',
        timestamp=timezone.now()
    )
        
@login_required
def user_activity_logs(request):
    if not request.user.is_superuser:
        return redirect('home')  # Redirect non-admin users away from this page

    # Get today's date
    today = timezone.localdate()  # This ensures it's using the local timezone's date.

    # Default to today's date if no date is provided
    from_date = request.GET.get('from_date', today)
    to_date = request.GET.get('to_date', today)

    # Ensure from_date and to_date are in date format
    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()

    # Convert the datetime to start of the day for from_date and end of the day for to_date
    from_date = timezone.make_aware(datetime.combine(from_date, datetime.min.time()))
    to_date = timezone.make_aware(datetime.combine(to_date, datetime.max.time()))

    # Get the activities within the date range
    activities = UserActivity.objects.filter(timestamp__range=(from_date, to_date))

    # Order activities by timestamp (most recent first)
    activities = activities.order_by('-timestamp')

    # Render the template with the filtered activities
    return render(request, 'task_management_system_app/user_activity_logs.html', {
        'activities': activities,
        'from_date': from_date.date(),  # Use only the date part
        'to_date': to_date.date()       # Use only the date part
    })
@login_required
def home(request):
    # Get today's date
    today = datetime.today().date()
    users = User.objects.exclude(username='admin')  # Exclude admin user from regular users

    # Get the selected users from the GET parameters (for admin only)
    selected_users = request.GET.getlist('selected_users')  # List of selected users (array of usernames)
    selected_user_shifts = [request.session.get(f"shift_{user.username}") for user in users]
    # print(f'selected_user_shifts:{selected_user_shifts}') 
    
    
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
    
    # Initialize user_shifts dictionary before POST block
    user_shifts = {}  # Default initialization of user_shifts

    # Store selected users and their shift types in session when the form is submitted
    if request.method == 'POST':
        selected_users = request.POST.getlist('selected_users')  # List of selected usernames
        request.session['selected_users'] = selected_users  # Save the selected users
        # Loop over users and save their shift types
        for user in users:
            shift_type = request.POST.get(f"shift_{user.id}")
            request.session[f"shift_{user.username}"] = shift_type
            # print(f"Stored {shift_type} for {user.username} in session")
        
        user_shifts = {}
        for user in users:
            user_shift = request.session.get(f"shift_{user.username}", 'normal')
            user_shifts[user.username] = user_shift
            # print(f"User: {user.username}, Shift: {user_shift}") 

    # Display login success message only once
    if not request.session.get('has_logged_in', False):  # Check if the user has logged in before
        messages.success(request, "Login Successfully!")  # Set message
        request.session['has_logged_in'] = True  # Set flag to True

    # Admin view: show tasks for all users and allow user selection for filtering tasks
    if request.user.is_superuser:
        task_counts = {}
        task_names = {}
        total_hours = {}  # Dictionary to hold total hours for each user

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
            
            # Calculate total hours for this user
            total_hours_for_user = 0
            for task in user_tasks:
                if task.estimated_time:
                    if task.estimated_time < 60:
                        total_hours_for_user += task.estimated_time / 60  # Convert minutes to hours
                    else:
                        total_hours_for_user += task.estimated_time / 60  # Hours are already in hours
            total_hours[user.username] = total_hours_for_user

        # Prepare the data for the chart
        user_names = list(task_counts.keys())
        task_counts_values = list(task_counts.values())
        task_names_values = list(task_names.values())


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
            'total_hours': total_hours,  # Pass the total hours to the template
            'selected_user_shifts': selected_user_shifts,
            'user_shifts': user_shifts,  # Pass the user shifts to the template
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

        # Sort tasks by time extracted from the task name (optional sorting logic)
        tasks = sorted(tasks, key=lambda task: extract_time_from_task_name(task.task_name) or datetime.min)

         # Calculate hours and minutes for each task
        for task in tasks:
            if task.estimated_time:
                task.hours = task.estimated_time // 60  # Calculate hours
                task.minutes = task.estimated_time % 60  # Calculate remaining minutes
            else:
                task.hours = 0
                task.minutes = 0
        
        # Calculate total hours for the logged-in user
        total_minutes_for_user = 0
        for task in tasks:
            if task.estimated_time:
                if task.estimated_time < 60:
                    total_minutes_for_user += task.estimated_time  # Add minutes directly
                else:
                    total_minutes_for_user += task.estimated_time  # Convert hours to minutes

        # Convert total minutes to hours and remaining minutes
        total_hours = total_minutes_for_user // 60
        remaining_minutes = total_minutes_for_user % 60

        # Render the template with tasks assigned to the logged-in user and filter parameters
        return render(request, 'home.html', {
            'tasks': tasks,
            'from_date': from_date,
            'to_date': to_date,
            'users': users,
            'selected_users': selected_users,  # Pass selected users here for the admin view
            'total_hours': total_hours,  # Total hours for the logged-in user
            'remaining_minutes': remaining_minutes,  # Remaining minutes after full hours
            'selected_user_shifts': selected_user_shifts,
            'user_shifts': user_shifts,  # Pass the user shifts to the template
        })

        
# Add a view for downloading tasks in Excel format
def download_tasks(request):
    # Get the current date in the correct timezone
    today = timezone.now().date()
    
    # Fetch tasks, filtered by today's date
    tasks = Task.objects.all()
    
    # Filter tasks by today's date (consider only the date part of the datetime)
    tasks = tasks.filter(start_date__gte=today, start_date__lt=today + timezone.timedelta(days=1))
    
    # Sort tasks by start_date in ascending order
    tasks = tasks.order_by('start_date')
    
    # Get the current user if logged in (assuming you're generating the report for a specific user)
    user = request.user
    if not user.is_superuser:  # If not admin, filter by logged-in user
        tasks = tasks.filter(assigned_to=user)
    
    # Function to convert estimated_time into the desired format
    def format_estimated_time(estimated_time):
        if estimated_time is None or estimated_time == 0:
            return "0 hours"
        hours = estimated_time // 60  # Get full hours
        minutes = estimated_time % 60  # Get remaining minutes
        time_string = ""
        if hours > 0:
            time_string += f"{hours} hour" + ("s" if hours > 1 else "")
        if minutes > 0:
            if hours > 0:
                time_string += " "
            time_string += f"{minutes} minute" + ("s" if minutes > 1 else "")
        return time_string

    # Function to calculate total estimated time in hours and minutes
    def calculate_total_estimated_time(tasks):
        total_minutes = sum(task.estimated_time for task in tasks if task.estimated_time)
        total_hours = total_minutes // 60
        total_remaining_minutes = total_minutes % 60
        return total_hours, total_remaining_minutes

    # Task data for Excel download
    tasks_data = {
        'Task Name': [task.task_name for task in tasks],
        'Assigned To': [task.assigned_to for task in tasks],
        'Start Date': [task.start_date.replace(tzinfo=None) if isinstance(task.start_date, datetime) and is_aware(task.start_date) else task.start_date for task in tasks],
        'End Date': [task.end_date.replace(tzinfo=None) if isinstance(task.end_date, datetime) and is_aware(task.end_date) else task.end_date for task in tasks],
        'Estimated Time': [
            format_estimated_time(task.estimated_time) for task in tasks
        ],
    }

    # Calculate total estimated time in hours and minutes
    total_hours, total_remaining_minutes = calculate_total_estimated_time(tasks)
    
    # Add the total row at the bottom
    total_row = {
        'Task Name': 'Total',
        'Assigned To': '',
        'Start Date': '',
        'End Date': '',
        'Estimated Time': f"{total_hours} hour{'s' if total_hours != 1 else ''} {total_remaining_minutes} minute{'s' if total_remaining_minutes != 1 else ''}"
    }

    # Append the total row to the tasks data
    tasks_data['Task Name'].append(total_row['Task Name'])
    tasks_data['Assigned To'].append(total_row['Assigned To'])
    tasks_data['Start Date'].append(total_row['Start Date'])
    tasks_data['End Date'].append(total_row['End Date'])
    tasks_data['Estimated Time'].append(total_row['Estimated Time'])

    # Convert to DataFrame
    df = pd.DataFrame(tasks_data)

    # Generate a dynamic file name based on the assigned user's username and today's date
    file_name = f"{user.username}_{today.strftime('%d-%m-%Y')}_tasks.xlsx"

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
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'task_management_system_app/register.html', {'form': form})

def LogoutPage(request):
    logout(request)
    messages.success(request, "Logout Successfully!")
    return redirect("login")

class TaskForm(forms.Form):
    
    class Meta:
        model = Task
        fields = ['task_name', 'category', 'assigned_to', 'start_date', 'end_date', 'estimated_time']
    task_name = forms.CharField(max_length=100)
    assigned_to = forms.CharField(max_length=100)
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    category = forms.CharField(max_length=100) 

# Load tasks from Excel file
def load_tasks_from_excel(file_path):
    try:
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            tasks = df[['Task Name', 'Estimated Time(in minutes)']].dropna()  # Remove rows with missing values
            tasks_list = [(row['Task Name'], row['Estimated Time(in minutes)']) for index, row in tasks.iterrows()]
            return tasks_list
        return []
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        return []

# Extract time from task name (task name is expected to have a time in it)
def extract_time_from_task_name(task_name):
    """
    Extract the time (e.g., '9:00 AM', '10:00 AM') from the task name and convert it to a datetime object.
    """
    try:
        # Task format: "CIT - KG hourly 9:00 AM EST report"
        time_str = task_name.split(' ')[-4] + ' ' + task_name.split(' ')[-3]  # Extract '9:00 AM'
        return datetime.strptime(time_str, '%I:%M %p')  # Convert to datetime object
    except Exception as e:
        print(f"Error extracting time: {e}")
        return None

# Filter tasks for Late Shift (from 11:00 AM to 08:00 PM)
def filter_late_shift_tasks(tasks):
    late_shift_start = datetime.strptime("11:00 AM", '%I:%M %p')
    late_shift_end = datetime.strptime("08:00 PM", '%I:%M %p')
    return [
        task for task in tasks
        if extract_time_from_task_name(task[0]) and late_shift_start <= extract_time_from_task_name(task[0]) <= late_shift_end
    ]

# Filter tasks for Normal Shift (from 09:00 AM to 06:00 PM)
def filter_normal_shift_tasks(tasks):
    normal_shift_start = datetime.strptime("09:00 AM", '%I:%M %p')
    normal_shift_end = datetime.strptime("06:00 PM", '%I:%M %p')
    return [
        task for task in tasks
        if extract_time_from_task_name(task[0]) and normal_shift_start <= extract_time_from_task_name(task[0]) <= normal_shift_end
    ]

# Function to filter tasks by shift type
def filter_tasks_by_shift(tasks, shift_type):
    if shift_type == 'late':
        return filter_late_shift_tasks(tasks)
    else:
        return filter_normal_shift_tasks(tasks)

# Assign tasks to the users based on shift and time constraints
def assign_tasks(request, tasks, users_list, success_message, is_daily_task=False, selected_users_shifts=None):
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        new_task_name = request.POST.get('new_task_name')
        assigned_to = request.POST.get('assigned_to')
        shift_type = request.POST.get('shift_type')

        # Validate start and end dates
        if not start_date or not end_date:
            messages.error(request, 'Please select both start and end dates.')
            return redirect('create_daily_task' if is_daily_task else 'create_task')

        # If new task name and assigned user are provided, create a task manually
        if new_task_name and assigned_to:
            try:
                assigned_user = User.objects.get(username=assigned_to)

                # Create and save the new task
                Task.objects.create(
                    task_name=new_task_name,
                    assigned_to=assigned_user,
                    start_date=start_date,
                    end_date=end_date,
                    estimated_time=request.POST.get('estimated_time')
                )
                messages.success(request, f"Task '{new_task_name}' has been created and assigned to {assigned_to}.")
                return redirect('create_daily_task' if is_daily_task else 'create_task')

            except User.DoesNotExist:
                messages.error(request, 'The selected user does not exist.')
                return redirect('create_daily_task' if is_daily_task else 'create_task')

        # Automatically assign tasks from the loaded Excel file if no new task is entered
        elif tasks and users_list:
            # Initialize users' total assigned time
            users_time = {user: 0 for user in users_list}
            task_assignments = []
            
            # Shuffle tasks to randomize the assignment order
            random.shuffle(tasks)

            # Sort tasks based on estimated time (longer tasks first)
            tasks.sort(key=lambda x: x[1], reverse=True)

            for task_name, estimated_time in tasks:
                task_time = extract_time_from_task_name(task_name)

                # Before 09:00 AM, assign tasks only to normal shift users
                if task_time and task_time < datetime.strptime("09:00 AM", '%I:%M %p'):
                    available_users = [user for user in users_list if selected_users_shifts[user.username] == 'normal']
                # Between 09:00 AM and 06:00 PM, assign to both normal and late shift users
                elif task_time and datetime.strptime("09:00 AM", '%I:%M %p') <= task_time <= datetime.strptime("05:30 PM", '%I:%M %p'):
                    available_users = [user for user in users_list if selected_users_shifts[user.username] in ['normal', 'late']]
                # Between 11:00 AM and 08:00 PM, assign to late shift users
                elif task_time and datetime.strptime("11:30 AM", '%I:%M %p') <= task_time <= datetime.strptime("08:00 PM", '%I:%M %p'):
                    available_users = [user for user in users_list if selected_users_shifts[user.username] == 'late']
                else:
                    continue  # Skip tasks that don't fit the time range

                # Ensure late shift users do not receive tasks before 11:00 AM
                if task_time and task_time < datetime.strptime("11:30 AM", '%I:%M %p'):
                    available_users = [user for user in available_users if selected_users_shifts[user.username] == 'normal']
                
                # Ensure that after 5:00 PM tasks go strictly to late shift users
                if task_time and task_time > datetime.strptime("06:00 PM", '%I:%M %p'):
                    available_users = [user for user in available_users if selected_users_shifts[user.username] == 'late']

                # Assign task to user with least total assigned time
                least_assigned_user = min(available_users, key=lambda u: users_time[u])
                assigned_user = least_assigned_user

                # Create the task and assign it to the selected user
                Task.objects.create(
                    task_name=task_name,
                    assigned_to=assigned_user,
                    start_date=start_date,
                    end_date=end_date,
                    estimated_time=estimated_time
                )

                # Update the user's total assigned time
                users_time[assigned_user] += estimated_time
                task_assignments.append(task_name)

            # Success message
            messages.success(request, f'{len(task_assignments)} tasks have been successfully assigned!')
            return redirect('create_daily_task' if is_daily_task else 'create_task')

        else:
            messages.error(request, 'No tasks or users found to assign tasks to.')

    # Render the page with the users and tasks data and the shifts for each user
    return render(request, 'task_management_system_app/create_task.html' if not is_daily_task else 'task_management_system_app/create_daily_task.html', {
        'users': users_list,
        'tasks': tasks,
        'selected_users_shifts': selected_users_shifts  # Ensure this is passed to the template
    })

@login_required
def create_task(request):
    excel_file_path = "tasks.xlsx"
    tasks = load_tasks_from_excel(excel_file_path)

    # Get selected users from the session
    selected_users_usernames = request.session.get('selected_users', [])

    # Fetch users from the database, filtering by selected usernames
    users = User.objects.filter(username__in=selected_users_usernames)
    users_list = list(users)

    # Get the shifts for each user from the session
    selected_users_shifts = {
        user.username: request.session.get(f"shift_{user.username}", "normal")  # Default to "normal" if no shift stored
        for user in users_list
    }

    # Call helper function to handle task creation
    return assign_tasks(request, tasks, users_list, 'create_task', is_daily_task=False, selected_users_shifts=selected_users_shifts)

def assign_tasks1(request, tasks, users_list, success_message, is_daily_task=False):
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
                    end_date=end_date,
                    estimated_time=request.POST.get('estimated_time')  # You will need to get this value from the form
                )
                messages.success(request, f"Task '{new_task_name}' has been created and assigned to {assigned_to}.")
                return redirect('create_daily_task' if is_daily_task else 'create_task')

            except User.DoesNotExist:
                messages.error(request, 'The selected user does not exist.')
                return redirect('create_daily_task' if is_daily_task else 'create_task')

        # Case 2: If no new task is entered, proceed to automatic task assignment from the Excel or predefined tasks
        elif tasks and users_list:
            # Sort the tasks based on estimated time (largest first)
            tasks.sort(key=lambda x: x[1], reverse=True)

            # Initialize users' total assigned time
            users_time = {user: 0 for user in users_list}

            # Track assignments to ensure each task is assigned to a user
            task_assignments = []

            # Assign tasks to users in a way that balances their estimated times
            for task_name, estimated_time in tasks:
                # Find the user with the least assigned time
                least_assigned_user = min(users_time, key=users_time.get)

                # Assign the task to this user
                assigned_user = least_assigned_user
                Task.objects.create(
                    task_name=task_name,
                    assigned_to=assigned_user,
                    start_date=start_date,
                    end_date=end_date,
                    estimated_time=estimated_time  # Use the estimated time from Excel
                )

                # Update the total assigned time for this user
                users_time[assigned_user] += estimated_time

                task_assignments.append(task_name)

            # Show success message after assignment
            messages.success(request, f'{len(task_assignments)} tasks have been automatically assigned to users successfully!')
            return redirect('create_daily_task' if is_daily_task else 'create_task')

        else:
            messages.error(request, 'No tasks or users found to assign tasks to.')

    # Rendering directly with hard-coded templates
    return render(request, 'task_management_system_app/create_daily_task.html' if is_daily_task else 'task_management_system_app/create_task.html', {'users': users_list, 'tasks': tasks})

# The actual view to create daily tasks
def create_daily_task(request):
    excel_file_path = "tasks1.xlsx"
    tasks = load_tasks_from_excel(excel_file_path)

    # Get selected users from the session (store the selected users in session in the home view)
    selected_users_usernames = request.session.get('selected_users', [])

    # Fetch users from the database, excluding the admin user, and filter by selected usernames
    users = User.objects.filter(username__in=selected_users_usernames)
    users_list = list(users)

    # Call helper function to handle task creation
    return assign_tasks1(request, tasks, users_list, 'create_daily_task', is_daily_task=True)

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

@login_required
@admin_required
def view_task_list(request):
    # Get the 'from_date' and 'to_date' from the GET request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Get the search query from the combined search box
    search_query = request.GET.get('search_query', '')  # This is the search term for tasks and assigned users
    
    # Get the current date to filter tasks by today's date
    today = datetime.today().date()

    # Capture the 'late_shift_user' from the request (if it's passed from the frontend)
    late_shift_user = request.GET.get('late_shift_user')

    # Filter tasks for the logged-in user (for regular users)
    tasks = Task.objects.all()
    
    # Admins can see all tasks
    if request.user.is_superuser:
        if late_shift_user:
            # Handle late shift user logic (update tasks assigned to this user)
            tasks = tasks.filter(assigned_to__username=late_shift_user)
            # Perform any additional logic related to the late shift user (e.g., notify or change task assignments)
            # Example: Assign the late shift user to a task that was previously unassigned
            tasks.update(assigned_to=User.objects.get(username=late_shift_user))
        
    else:
        # Regular users can see only their own tasks
        tasks = tasks.filter(assigned_to=request.user)

    # Apply filtering based on dates (from_date and to_date)
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

    # Filtering by the combined search query (task name or assigned user)
    if search_query:
        tasks = tasks.filter(
            task_name__icontains=search_query
        ) | tasks.filter(assigned_to__username__icontains=search_query)
    
    # Calculate total estimated hours for each user
    user_hours = {}
    for task in tasks:
        if task.assigned_to:
            if task.assigned_to.username not in user_hours:
                user_hours[task.assigned_to.username] = 0
            user_hours[task.assigned_to.username] += task.estimated_time
    
    # Convert estimated time into hours and minutes format
    user_hours_display = {}
    for user, total_minutes in user_hours.items():
        hours = total_minutes // 60
        minutes = total_minutes % 60
        user_hours_display[user] = f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"
    
    # Calculate hours and minutes for each task
    for task in tasks:
        if task.estimated_time:
            task.hours = task.estimated_time // 60  # Calculate hours
            task.minutes = task.estimated_time % 60  # Calculate remaining minutes
        else:
            task.hours = 0
            task.minutes = 0

    # Sort tasks by time extracted from the task name
    tasks = sorted(tasks, key=lambda task: extract_time_from_task_name(task.task_name) or datetime.min)
    
    # Get the list of users based on session or return all users
    selected_users_usernames = request.session.get('selected_users', [])
    
    # Get the list of users for dropdown
    if selected_users_usernames:
        users = User.objects.filter(username__in=selected_users_usernames)
    else:
        users = User.objects.filter(is_superuser=False)  # Exclude admin users
    
    users_list = list(users)
    
    # Pass the full list of users and filtered tasks to the template
    return render(request, 'view_task_list.html', {
        'tasks': tasks,
        'from_date': from_date,
        'to_date': to_date,
        'users_list': users_list,  # Pass the list of users to the template for dropdown
        'search_query': search_query,  # Include the search term in the template
        'user_hours_display': user_hours_display,  # Pass the user total estimated hours data
        'late_shift_user': late_shift_user  # Pass the late shift user to the template
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

