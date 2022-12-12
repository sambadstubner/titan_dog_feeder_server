"""
FLASK APP for Amani Pet Products v.1
Started: 9/30/2022
Will be the prototyping user interface for users to see status of feeder, update schedule, and feed now

REQUIRED ROUTES:
/index
 - Home page to direct users to create user or login
/createUser
 - Create user in Firebase
 - Assign feeder to user
/login
 - log user in
/<user_id>
 - For each feeder:
   - Show the current schedule
   - Provide options to update schedule
   - Provide option to feed now
   - Show dog food capacity level
/updateSchedule
 - Update schedule values in Firebase
 - Redirect user to /<user_id>
/feedNow
 - Update feedNow flag in Firebase
 - Wait for acknowledgement
 - Display that it fed the desired amount
 - Redirect to /<user_id>
"""

from datetime import datetime, timedelta, timezone
import pytz

from flask import Flask, render_template, request, redirect
from flask_wtf import FlaskForm
from wtforms import TimeField, IntegerField, validators, SubmitField, StringField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap

import firebase_admin
from firebase_admin import credentials, db

# setup firebase
cred = credentials.Certificate("fb_key.json")
fb = firebase_admin.initialize_app(cred, name="server_v1")
db_url = "https://esp32-b7cbf-default-rtdb.firebaseio.com/"

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret key"
Bootstrap(app)

MST = pytz.timezone("US/Mountain")


class loginFeeder(FlaskForm):
    feeder_id = StringField("Unique feeder id:", validators=[DataRequired()])
    submit = SubmitField("Submit")


@app.route("/", methods=["GET", "POST"])
def index():
    form = loginFeeder(request.form)
    if request.method == "GET":
        return render_template("index.html", form=form)
    if form.validate_on_submit():
        feeder_id = form.feeder_id.data
        return redirect("/" + str(feeder_id))


@app.route("/<feeder_id>/feedNow", methods=["GET", "POST"])
def feedNow(feeder_id):
    ref = db.reference(path=feeder_id + "/feedNow", app=fb, url=db_url)
    if request.method == "POST":
        ref.set(True)
        return render_template(
            "feeding.html",
            feeder_id=feeder_id,
        )
    if request.method == "GET":
        if ref.get() == True:
            return redirect("/" + str(feeder_id))
        else:
            return render_template("unsuccessful.html", feeder_id=feeder_id)


@app.route("/<feeder_id>", methods=["GET"])
def home(feeder_id):
    ref = db.reference(path=feeder_id, app=fb, url=db_url)
    children = ref.get()
    schedule = children["schedule"]
    return render_template("home.html", feeder_id=feeder_id, schedule=schedule)


@app.route("/<feeder_id>/editSchedule", methods=["GET", "POST"])
def editSchedule(feeder_id):

    # Get schedule from db
    ref = db.reference(path=feeder_id + "/schedule", app=fb, url=db_url)
    schedule = ref.get()

    amount = []
    time = []
    for key, value in schedule.items():
        time.append(key)
        amount.append(value)

    # Create form
    class EditScheduleForm(FlaskForm):
        pass

    for i in range(len(schedule)):
        setattr(
            EditScheduleForm,
            "t" + str(i),
            TimeField(
                "Time",
                format="%H:%M",
                default=datetime.strptime(time[i], "%H:%M"),
            ),
        )
        setattr(
            EditScheduleForm,
            "a" + str(i),
            IntegerField(
                "Amount", [validators.NumberRange(min=0, max=30)], default=amount[i]
            ),
        )
        setattr(EditScheduleForm, "d" + str(i), SubmitField("Delete"))
    setattr(EditScheduleForm, "submit", SubmitField("Submit"))
    setattr(EditScheduleForm, "add", SubmitField("Add"))

    form = EditScheduleForm(request.form)

    if request.method == "GET":
        return render_template(
            "editSchedule.html", feeder_id=feeder_id, schedule=schedule, form=form
        )
    if request.method == "POST":
        result = {}
        amount = []
        time = []

        for field in form:
            if field.name[0] == "d":
                if field.data:
                    index = field.name[1]
                    for t_field in form:
                        if t_field.name == ("t" + index):
                            return redirect(
                                "/"
                                + str(feeder_id)
                                + "/editSchedule/delete/"
                                + t_field.data.strftime("%H:%M")
                            )
        if form.add.data:
            return redirect("/" + str(feeder_id) + "/editSchedule/add")
        if form.validate_on_submit():
            for field in form:
                if field.name[0] == "t":
                    time.append(field.data.strftime("%H:%M"))
                if field.name[0] == "a":
                    amount.append(field.data)
            for i in range(len(time)):
                result[time[i]] = amount[i]
            print(result)
            ref.set(result)
        return redirect("/" + str(feeder_id))


@app.route("/<feeder_id>/editSchedule/add")
def add(feeder_id):
    # Get schedule from db
    ref = db.reference(path=feeder_id + "/schedule", app=fb, url=db_url)
    schedule = ref.get()
    now = datetime.now(MST)
    unique = False
    delta = timedelta(minutes=1)
    while unique == False:
        if now.strftime("%H:%M") in schedule:
            now = now + delta
        else:
            schedule[now.strftime("%H:%M")] = 0
            unique = True

    print(schedule)
    ref.set(schedule)
    return redirect("/" + str(feeder_id) + "/editSchedule")


@app.route("/<feeder_id>/editSchedule/delete/<time>")
def delete(feeder_id, time):
    # Get schedule from db
    ref = db.reference(path=feeder_id + "/schedule", app=fb, url=db_url)
    schedule = ref.get()
    del schedule[time]
    print(schedule)
    ref.set(schedule)
    return redirect("/" + str(feeder_id) + "/editSchedule")


if __name__ == "__main__":
    app.run(debug=True)
