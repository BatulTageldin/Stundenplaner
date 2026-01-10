from flask import Flask, redirect, render_template, request, url_for
from dotenv import load_dotenv
import os
import git
import hmac
import hashlib
from db import db_read, db_write
from auth import login_manager, authenticate, register_user
from flask_login import login_user, logout_user, login_required, current_user
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Load .env variables
load_dotenv()
W_SECRET = os.getenv("W_SECRET")

# Init flask app
app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = "supersecret"

# Init auth
login_manager.init_app(app)
login_manager.login_view = "login"

# DON'T CHANGE
def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

# DON'T CHANGE
@app.post('/update_server')
def webhook():
    x_hub_signature = request.headers.get('X-Hub-Signature')
    if is_valid_signature(x_hub_signature, request.data, W_SECRET):
        repo = git.Repo('./mysite')
        origin = repo.remotes.origin
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200
    return 'Unauthorized', 401


# -----------------------------
# STARTSEITE
# -----------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for("week_view"))
        elif current_user.role == 'teacher':
            return redirect(url_for("teacher_week"))
    return redirect(url_for("login"))


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user = authenticate(
            request.form["username"],
            request.form["password"]
        )

        if user:
            login_user(user)
            return redirect(url_for("index"))

        error = "Benutzername oder Passwort ist falsch."

    return render_template(
        "auth.html",
        title="In dein Konto einloggen",
        action=url_for("login"),
        button_label="Einloggen",
        error=error,
        footer_text="Noch kein Konto?",
        footer_link_url=url_for("register"),
        footer_link_label="Registrieren",
        show_role=False
    )


# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        user_id = register_user(username, password, role)
        if user_id:
            if role == 'teacher':
                # Add to lehrer table
                db_write("INSERT INTO lehrer (name, user_id) VALUES (%s, %s)", (username, user_id))
            return redirect(url_for("login"))

        error = "Benutzername existiert bereits."

    return render_template(
        "auth.html",
        title="Neues Konto erstellen",
        action=url_for("register"),
        button_label="Registrieren",
        error=error,
        footer_text="Du hast bereits ein Konto?",
        footer_link_url=url_for("login"),
        footer_link_label="Einloggen",
        show_role=True
    )


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# -----------------------------
# FACH HINZUFÜGEN
# -----------------------------
@app.route("/lesson/add", methods=["GET", "POST"])
@login_required
def add_lesson():
    if request.method == "POST":
        subject = request.form["subject"]


        if current_user.role == 'teacher':
            lehrer = db_read("SELECT id FROM lehrer WHERE user_id=%s", (current_user.id,), single=True)
            if not lehrer:
                # Error, but for now redirect
                return redirect(url_for("teacher_week"))
            lehrer_id = lehrer["id"]
        else:
            lehrer_id = request.form["teacher"]
        room_number = request.form.get("room", "unbekannt")
        weekday = request.form["weekday"]
        start, end = request.form["timeblock"].split("-")


        # Wochentag von Zahl → Text
        tage = {
            "1": "Montag",
            "2": "Dienstag",
            "3": "Mittwoch",
            "4": "Donnerstag",
            "5": "Freitag"
        }
        tag = tage[weekday]

        # Raum speichern oder finden
        raum = db_read(
            "SELECT id FROM raum WHERE raumnummer=%s",
            (room_number,),
            single=True
        )
        if not raum:
            db_write("INSERT INTO raum (raumnummer) VALUES (%s)", (room_number,))
            raum = db_read(
                "SELECT id FROM raum WHERE raumnummer=%s",
                (room_number,),
                single=True
            )

        # Fach speichern oder finden
        fach = db_read(
            "SELECT id FROM faecher WHERE fachname=%s AND lehrer_id=%s AND raum_id=%s AND tag=%s AND startzeit=%s AND endzeit=%s",
            (subject, lehrer_id, raum["id"], tag, start, end),
            single=True
        )
        if not fach:
            db_write(
                "INSERT INTO faecher (fachname, lehrer_id, raum_id, tag, startzeit, endzeit) VALUES (%s,%s,%s,%s,%s,%s)",
                (subject, lehrer_id, raum["id"], tag, start, end)
            )
            fach = db_read(
                "SELECT id FROM faecher WHERE fachname=%s AND lehrer_id=%s AND raum_id=%s AND tag=%s AND startzeit=%s AND endzeit=%s",
                (subject, lehrer_id, raum["id"], tag, start, end),
                single=True
            )

        return redirect(url_for("teacher_week"))

    return render_template("lesson.html")


# -----------------------------
# LEHRER HINZUFÜGEN
# -----------------------------
@app.route("/teacher/add", methods=["GET", "POST"])
@login_required
def add_teacher():
    if request.method == "POST":
        name = request.form["name"]

        # Check if teacher already exists
        existing = db_read(
            "SELECT id FROM lehrer WHERE name=%s",
            (name,),
            single=True
        )
        if existing:
            # Maybe add error handling, but for now just redirect
            return redirect(url_for("week_view"))

        # Insert new teacher
        db_write("INSERT INTO lehrer (name) VALUES (%s)", (name,))

        return redirect(url_for("week_view"))

    return render_template("teacher.html")


# -----------------------------
# STUNDENPLAN AKTUALISIEREN
# -----------------------------
@app.route("/schedule/add", methods=["GET", "POST"])
@login_required
def add_schedule():
    if request.method == "POST":
        fach_id = request.form["fach"]

        # Stundenplan-Eintrag speichern
        db_write(
            "INSERT INTO stundenplan (user_id, fach_id) VALUES (%s,%s)",
            (current_user.id, fach_id)
        )

        return redirect(url_for("week_view"))

    faecher = db_read("""
        SELECT 
            faecher.id,
            faecher.fachname,
            lehrer.name AS lehrer,
            raum.raumnummer AS raum,
            faecher.tag,
            faecher.startzeit,
            faecher.endzeit
        FROM faecher
        JOIN lehrer ON faecher.lehrer_id = lehrer.id
        JOIN raum ON faecher.raum_id = raum.id
        ORDER BY faecher.fachname
    """) or []
    return render_template("schedule.html", faecher=faecher)


# -----------------------------
# STUNDENPLAN EINTRAG LÖSCHEN
# -----------------------------
@app.route("/schedule/delete/<int:stundenplan_id>", methods=["POST"])
@login_required
def delete_schedule(stundenplan_id):
    # Ensure the entry belongs to the current user
    entry = db_read(
        "SELECT id FROM stundenplan WHERE id=%s AND user_id=%s",
        (stundenplan_id, current_user.id),
        single=True
    )
    if entry:
        db_write("DELETE FROM stundenplan WHERE id=%s", (stundenplan_id,))
    
    return redirect(url_for("week_view"))


# -----------------------------
# STUNDENPLAN EINTRAG BEARBEITEN
# -----------------------------
@app.route("/schedule/edit/<int:stundenplan_id>", methods=["GET", "POST"])
@login_required
def edit_schedule(stundenplan_id):
    # Ensure the entry belongs to the current user
    entry = db_read(
        "SELECT id, fach_id FROM stundenplan WHERE id=%s AND user_id=%s",
        (stundenplan_id, current_user.id),
        single=True
    )
    if not entry:
        return redirect(url_for("week_view"))

    if request.method == "POST":
        new_fach_id = request.form["fach"]
        db_write("UPDATE stundenplan SET fach_id=%s WHERE id=%s", (new_fach_id, stundenplan_id))
        return redirect(url_for("week_view"))

    faecher = db_read("""
        SELECT 
            faecher.id,
            faecher.fachname,
            lehrer.name AS lehrer,
            raum.raumnummer AS raum,
            faecher.tag,
            faecher.startzeit,
            faecher.endzeit
        FROM faecher
        JOIN lehrer ON faecher.lehrer_id = lehrer.id
        JOIN raum ON faecher.raum_id = raum.id
        ORDER BY faecher.fachname
    """) or []

    return render_template("edit_schedule.html", faecher=faecher, current_fach_id=entry["fach_id"])


# -----------------------------
# STUNDENPLAN ANZEIGEN
# -----------------------------
@app.route("/week")
@login_required
def week_view():
    eintraege = db_read("""
        SELECT 
            stundenplan.id AS stundenplan_id,
            faecher.tag,
            faecher.startzeit,
            faecher.endzeit,
            faecher.fachname,
            lehrer.name AS lehrer,
            raum.raumnummer AS raum
        FROM stundenplan
        JOIN faecher ON stundenplan.fach_id = faecher.id
        JOIN lehrer ON faecher.lehrer_id = lehrer.id
        JOIN raum ON faecher.raum_id = raum.id
        WHERE stundenplan.user_id=%s
        ORDER BY FIELD(faecher.tag, 'Montag','Dienstag','Mittwoch','Donnerstag','Freitag'), faecher.startzeit
    """, (current_user.id,))

    # Struktur für Template
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
    stundenplan = {tag: [] for tag in wochentage}

    for e in eintraege:
        stundenplan[e["tag"]].append({
            "stundenplan_id": e["stundenplan_id"],
            "fachname": e["fachname"],
            "lehrer": e["lehrer"],
            "raum": e["raum"],

            # FIX: timedelta → String (HH:MM)
            "startzeit": str(e["startzeit"])[:5],
            "endzeit": str(e["endzeit"])[:5]
        })

    return render_template("student_week.html", stundenplan=stundenplan)


# -----------------------------
# LEHRER FAECHER ANZEIGEN
# -----------------------------
@app.route("/teacher/week")
@login_required
def teacher_week():
    if current_user.role != 'teacher':
        return redirect(url_for("week_view"))

    # Get lehrer_id for current user
    lehrer = db_read("SELECT id FROM lehrer WHERE user_id=%s", (current_user.id,), single=True)
    if not lehrer:
        # No lehrer entry, show empty
        stundenplan = {tag: [] for tag in ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]}
        return render_template("teacher_week.html", stundenplan=stundenplan)

    subjects = db_read("""
        SELECT 
            faecher.fachname,
            lehrer.name AS lehrer,
            raum.raumnummer AS raum,
            faecher.tag,
            faecher.startzeit,
            faecher.endzeit
        FROM faecher
        JOIN lehrer ON faecher.lehrer_id = lehrer.id
        JOIN raum ON faecher.raum_id = raum.id
        WHERE faecher.lehrer_id = %s
        ORDER BY FIELD(faecher.tag, 'Montag','Dienstag','Mittwoch','Donnerstag','Freitag'), faecher.startzeit
    """, (lehrer["id"],)) or []

    # Struktur für Template
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
    stundenplan = {tag: [] for tag in wochentage}

    for s in subjects:
        stundenplan[s["tag"]].append({
            "fachname": s["fachname"],
            "lehrer": s["lehrer"],
            "raum": s["raum"],
            "startzeit": str(s["startzeit"])[:5],
            "endzeit": str(s["endzeit"])[:5]
        })

    return render_template("teacher_week.html", stundenplan=stundenplan)


# -----------------------------
# START APP
# -----------------------------
if __name__ == "__main__":
    app.run()
