import pandas as pd
from datetime import datetime

def load_tasks_from_excel(file_path):
    """
    Loads tasks from the Excel file and returns a list of tasks.
    Each task is a tuple (task_name, estimated_time).
    """
    df = pd.read_excel(file_path)  # Read Excel file into DataFrame
    tasks = []
    
    for index, row in df.iterrows():
        task_name = row['Task Name']  # Assuming task names are in a column called 'Task Name'
        estimated_time = row['Estimated Time']  # Assuming estimated time is in a column called 'Estimated Time'
        tasks.append((task_name, estimated_time))
    
    return tasks

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

# Now use the functions to load tasks and extract times
file_path = "tasks.xlsx"
tasks = load_tasks_from_excel(file_path)

# Example of extracting time from task names
for task in tasks:
    task_name, estimated_time = task
    task_time = extract_time_from_task_name(task_name)
    if task_time:
        print(f"Task: {task_name}, Time: {task_time.strftime('%I:%M %p')}")
    else:
        print(f"Error extracting time for task: {task_name}")