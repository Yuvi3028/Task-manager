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
from .models import Task
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
                return redirect('category_list')
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

    # Initialize from_date and to_date as None by default
    from_date = None
    to_date = None
    tasks = Task.objects.all()  # Default to all tasks initially

    # Handle date range filter if provided in the GET request
    if 'from_date' in request.GET and 'to_date' in request.GET:
        try:
            # Parse the from_date and to_date from the GET request
            from_date = datetime.strptime(request.GET['from_date'], '%Y-%m-%d').date()
            to_date = datetime.strptime(request.GET['to_date'], '%Y-%m-%d').date()

            # Filter tasks based on the date range
            tasks = tasks.filter(start_date__gte=from_date, end_date__lte=to_date)
        except ValueError:
            pass  # Handle invalid date format gracefully

    # Admin view: show tasks for all users and generate task distribution chart
    if request.user.is_superuser:
        users = User.objects.all()
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

        # Render the template with chart data, filtered tasks, and filter parameters
        return render(request, 'home.html', {
            'user_names': json.dumps(user_names),
            'task_counts_values': json.dumps(task_counts_values),
            'task_names_values': json.dumps(task_names_values),
            'tasks': tasks,  # Pass the filtered tasks to the template
            'from_date': from_date,
            'to_date': to_date,
        })
    
    # For regular users: filter tasks for the logged-in user and the selected date range
    else:
        tasks = tasks.filter(assigned_to=request.user)

        if from_date and to_date:
            tasks = tasks.filter(start_date__gte=from_date, end_date__lte=to_date)
        else:
            # Default to today's tasks if no date range is provided
            tasks = tasks.filter(start_date__lte=today, end_date__gte=today)

        # Render the template with tasks assigned to the user
        return render(request, 'home.html', {
            'tasks': tasks,
            'from_date': from_date,
            'to_date': to_date,
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
        'Category': [task.category for task in tasks],
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

@login_required
def create_task(request):
    try:
        # Load tasks from Excel file (optional part)
        excel_file_path = "tasks.xlsx"
        if os.path.exists(excel_file_path):
            df = pd.read_excel(excel_file_path)
            tasks = df['Task Name'].dropna().tolist()  # List of task names from the Excel file
        else:
            tasks = []
    except Exception as e:
        print("Error loading Excel file:", e)
        tasks = []

    # Fetch users from the database, excluding the admin user
    users = User.objects.exclude(username='admin')

    if request.method == 'POST':
        # Get the start and end dates from the form
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Validate the dates
        if not start_date or not end_date:
            messages.error(request, 'Please select both start and end dates.')
            return redirect('create_task')

        # If there are tasks and users, proceed to automatically assign tasks
        if tasks and users:
            # Shuffle the list of tasks to randomize the order
            random.shuffle(tasks)

            # Shuffle users as well
            shuffled_users = list(users)  # List of all users
            random.shuffle(shuffled_users)

            # Track assignments to ensure each task is assigned to a user
            task_assignments = []

            # Assign tasks to users in a random order
            for i, task_name in enumerate(tasks):
                assigned_user = shuffled_users[i % len(shuffled_users)]  # Assign to a user randomly
                # Create the task for the user
                Task.objects.create(
                    task_name=task_name,
                    category=Category.objects.first(),  # Use the first available category or choose based on your logic
                    assigned_to=assigned_user,
                    start_date=start_date,
                    end_date=end_date
                )
                task_assignments.append(task_name)

            messages.success(request, f'{len(task_assignments)} tasks have been automatically assigned to users successfully!')
            return redirect('create_task')
        else:
            messages.error(request, 'No tasks or users found to assign tasks to.')

    else:
        form = TaskForm()

    context = {
        'form': form,
        'users': users,  # Pass the filtered users to the template
        'categories': Category.objects.all(),
        'tasks': tasks,
    }

    return render(request, 'task_management_system_app/create_task.html', context)


def save_to_excel(cleaned_data):
    excel_file_path = os.path.join(BASE_DIR, "Assigned_tasks.xlsx")
    
    # Prepare the data dictionary
    task_data = {
        "Task Name": form.cleaned_data['task_name'],
        "Category": form.cleaned_data['category'],
        "Start Date": form.cleaned_data['start_date'],
        "End Date": form.cleaned_data['end_date'],
        # "Priority": form.cleaned_data['priority'],
        # "Description": form.cleaned_data['description'],
        # "Location": form.cleaned_data.get('location', ""),
        # "Organizer": form.cleaned_data['organizer'],
        "Assigned To": form.cleaned_data['assigned_to']  # Ensure this is populated
    }

    # Log the data to ensure it's correct
    print("Task Data to Save to Excel:", task_data)

    try:
        # If file exists, append the new data to it
        if os.path.exists(excel_file_path):
            print("Excel file exists, reading existing data...")
            df_existing = pd.read_excel(excel_file_path)
            print("Existing Data Loaded:", df_existing)
            df = pd.concat([df_existing, pd.DataFrame(task_data)], ignore_index=True)
        else:
            print("Excel file does not exist. Creating a new file...")
            df = pd.DataFrame(task_data)
        
        # Log final DataFrame before saving
        print("DataFrame to Save:", df)

        # Write the data to Excel
        df.to_excel(excel_file_path, index=False, engine='openpyxl')
        print("Data saved to Excel successfully at:", excel_file_path)
    except Exception as e:
        print("Excel Save Error:", e)




# @login_required
# @admin_required
# def update_task(request):
#     task = Task.objects.all()
#     if request.method == 'POST':
#         # Update task fields based on form data
#         task.name = request.POST.get('name')
#         task.start_date = request.POST.get('start_date')
#         task.end_date = request.POST.get('end_date')
#         task.category = request.POST.get('category')
#         # task.description = request.POST.get('description')
#         # task.location = request.POST.get('location')
#         # task.organizer = request.POST.get('organizer')
#         task.assigned_to = request.POST.get('assigned_to')
#         task.save()
#         return redirect('home')
#     else:
#         # Render update task page with task data
#         return render(request, 'task_management_system_app/update_task.html', {'task': task})

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

        # Check if the request is an AJAX request and respond accordingly
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})  # Return a JSON response for AJAX

        return redirect('view_task_list')  # Redirect back to task list after deletion

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
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            tasks = tasks.filter(start_date__gte=from_date)

        if to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            tasks = tasks.filter(end_date__lte=to_date)
            
        else:
            # Default to today's date if no date filter is provided
            tasks = tasks.filter(start_date__lte=today, end_date__gte=today)
    else:
        # Regular users can see their own tasks only
        tasks = tasks.filter(assigned_to=request.user)

        if from_date:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            tasks = tasks.filter(start_date__gte=from_date)

        if to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            tasks = tasks.filter(end_date__lte=to_date)
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