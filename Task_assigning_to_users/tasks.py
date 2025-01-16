from models import db, User
import random


def assign_daily_tasks():
    # Fetch all users
    users = User.query.all()
    
    # Example predefined tasks
    tasks = [
        "Check emails",
        "Attend team meeting",
        "Update project documentation",
        "Work on code review",
        "Prepare presentation slides",
    ]
    
    # Randomly assign a task to each user
    for user in users:
        user.daily_task = random.choice(tasks)
    db.session.commit()
    print("Daily tasks have been assigned!")
