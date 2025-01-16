from flask import Flask, render_template, request, redirect, url_for, session
from models import db, User
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.daily import DailyTrigger
from tasks import assign_daily_tasks
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from tasks import assign_daily_tasks

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
app.config["SECRET_KEY"] = "your_secret_key_here"

db.init_app(app)

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(assign_daily_tasks, CronTrigger(hour=0, minute=0))  # Schedule daily at midnight


@app.before_request
def create_tables():
    app.before_request_funcs[None].remove(create_tables)
    db.create_all()
    print("Before the first request!")
    


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user:
            return "User already exists!"
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("index.html")


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))
    user = User.query.get(session["user_id"])
    return render_template("dashboard.html", task=user.daily_task)


if __name__ == "__main__":
    app.run(debug=True)
