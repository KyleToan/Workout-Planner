import os
import json 
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# Configure application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Routine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    exercises_json = db.Column(db.Text, nullable=True)  # JSON list of exercises
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('routines', lazy=True))

def create_tables():
    with app.app_context():
        db.create_all()

def fromjson_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return []
    
app.jinja_env.filters['fromjson'] = fromjson_filter

    
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/greet", methods=["POST"])
def greet():
    name = request.form.get("name")
    return render_template("greet.html", name=name)

@app.route("/about")
def about():
    return render_template("about_us.html")

@app.route("/get_started", methods=["GET", "POST"])
def get_started():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if not username or not password or not confirm_password:
            error = "All fields are required."
            return render_template("get_started.html", error=error)
        if password != confirm_password:
            error = "Passwords do not match."
            return render_template("get_started.html", error=error, username=username)
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return render_template("registered.html", username=username)
    return render_template("get_started.html")

@app.route("/log_in", methods=["GET", "POST"])
def log_in():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return render_template("main_page.html", username=username)
        else:
            error = "Invalid username or password."
            return render_template("log_in.html", error=error)
    return render_template("log_in.html")

@app.route("/main_page", methods=["GET", "POST"])
def main_page():
    return render_template("main_page.html")

@app.route("/exercises", methods=["GET", "POST"])
def exercises():
    return render_template("exercises.html")

@app.route("/routines")
def routines():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('log_in'))
    routines = Routine.query.filter_by(user_id=user_id).order_by(Routine.created_at.desc()).all()
    return render_template("routines.html", routines=routines)

@app.route("/routines/new", methods=["GET", "POST"])
def new_routine():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('log_in'))
    if request.method == "POST":
        name = request.form.get("name") or "Untitled"
        notes = request.form.get("notes", "")
        exercises_text = request.form.get("exercises", "")
        exercises = [line.strip() for line in exercises_text.splitlines() if line.strip()]
        r = Routine(user_id=user_id, name=name, notes=notes, exercises_json=json.dumps(exercises))
        db.session.add(r)
        db.session.commit()
        return redirect(url_for("routines"))
    return render_template("new_routine.html")

@app.route("/routines/<int:routine_id>")
def routine_detail(routine_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('log_in'))
    r = Routine.query.get_or_404(routine_id)
    if r.user_id != user_id:
        abort(403)
    exercises = json.loads(r.exercises_json or "[]")
    return render_template("routine_detail.html", routine=r, exercises=exercises)

@app.route("/routines/<int:routine_id>/delete", methods=["POST"])
def delete_routine(routine_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('log_in'))
    r = Routine.query.get_or_404(routine_id)
    if r.user_id != user_id:
        abort(403)
    db.session.delete(r)
    db.session.commit()
    return redirect(url_for("routines"))

@app.route("/nutrition", methods=["GET", "POST"])
def nutrition():
    if request.method == "POST":
        age = int(request.form.get("age"))
        weight = float(request.form.get("weight"))
        height = float(request.form.get("height"))
        gender = request.form.get("gender")
        activity_level = request.form.get("activity_level")

        weight = weight / 2.205
        height = height * 2.54
        if gender == "male":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        if activity_level == "0":
            caloric_intake = bmr * 1.2
        elif activity_level == "1":
            caloric_intake = bmr * 1.375
        elif activity_level == "2":
            caloric_intake = bmr * 1.55
        elif activity_level == "3":
            caloric_intake = bmr * 1.725
        elif activity_level == "4":
            caloric_intake = bmr * 1.9
        caloric_intake = round(caloric_intake)
        bmr = round(bmr)

        carbs = caloric_intake * 0.5
        protein = caloric_intake * 0.2
        fats = caloric_intake * 0.3

        carbs = carbs / 4
        protein = protein / 4
        fats = fats / 9

        carbs = round(carbs)
        protein = round(protein)
        fats = round(fats)

        return render_template("nutrition.html", bmr=bmr, caloric_intake=caloric_intake, carbs=carbs, protein=protein, fats=fats)
    return render_template("nutrition.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return render_template("index.html")

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)