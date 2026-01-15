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

        # Check for time conflicts - teacher can't have multiple classes at the same time
        conflict = db_read("""
            SELECT id FROM faecher 
            WHERE lehrer_id=%s AND tag=%s AND startzeit=%s AND endzeit=%s
        """, (lehrer_id, tag, start, end), single=True)
        
        if conflict:
            # Teacher already has a class at this time
            return render_template("lesson.html", error="Du hast bereits ein Fach zu dieser Zeit!")

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
# STUNDENPLAN AKTUALISIEREN
# -----------------------------
@app.route("/schedule/add", methods=["GET", "POST"])
@login_required
def add_schedule():
    if request.method == "POST":
        fach_id = request.form["fach_id"]

        # Check if already added
        existing = db_read(
            "SELECT id FROM stundenplan WHERE user_id=%s AND fach_id=%s",
            (current_user.id, fach_id),
            single=True
        )
        if existing:
            # Already added, perhaps flash message, but for now redirect
            return redirect(url_for("week_view"))
        
        # Check for time conflicts - student can't enroll in multiple classes at the same time
        conflict = db_read("""
            SELECT stundenplan.id FROM stundenplan
            JOIN faecher f1 ON stundenplan.fach_id = f1.id
            JOIN faecher f2 ON f2.id = %s
            WHERE stundenplan.user_id = %s 
            AND f1.tag = f2.tag 
            AND f1.startzeit = f2.startzeit 
            AND f1.endzeit = f2.endzeit
        """, (fach_id, current_user.id), single=True)
        
        if conflict:
            # Student already has a class at this time
            available_faecher = db_read("""
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
                LEFT JOIN stundenplan ON faecher.id = stundenplan.fach_id AND stundenplan.user_id = %s
                WHERE stundenplan.id IS NULL
                ORDER BY faecher.fachname, faecher.tag, faecher.startzeit
            """, (current_user.id,)) or []
            return render_template("schedule.html", available_faecher=available_faecher, error="Du hast bereits ein Fach zu dieser Zeit!")

        # Stundenplan-Eintrag speichern
        db_write(
            "INSERT INTO stundenplan (user_id, fach_id) VALUES (%s,%s)",
            (current_user.id, fach_id)
        )

        return redirect(url_for("week_view"))

    # Get available faecher (not already in user's stundenplan)
    available_faecher = db_read("""
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
        LEFT JOIN stundenplan ON faecher.id = stundenplan.fach_id AND stundenplan.user_id = %s
        WHERE stundenplan.id IS NULL
        ORDER BY faecher.fachname, faecher.tag, faecher.startzeit
    """, (current_user.id,)) or []

    return render_template("schedule.html", available_faecher=available_faecher)


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
            faecher.id AS fach_id,
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
            "fach_id": s["fach_id"],
            "fachname": s["fachname"],
            "lehrer": s["lehrer"],
            "raum": s["raum"],
            "startzeit": str(s["startzeit"])[:5],
            "endzeit": str(s["endzeit"])[:5]
        })

    return render_template("teacher_week.html", stundenplan=stundenplan)


# -----------------------------
# LEHRER FACH LÖSCHEN
# -----------------------------
@app.route("/lesson/delete/<int:fach_id>", methods=["POST"])
@login_required
def delete_lesson(fach_id):
    if current_user.role != 'teacher':
        return redirect(url_for("week_view"))
    
    # Get lehrer_id for current user
    lehrer = db_read("SELECT id FROM lehrer WHERE user_id=%s", (current_user.id,), single=True)
    if not lehrer:
        return redirect(url_for("teacher_week"))
    
    # Ensure the lesson belongs to the current teacher
    fach = db_read(
        "SELECT id FROM faecher WHERE id=%s AND lehrer_id=%s",
        (fach_id, lehrer["id"]),
        single=True
    )
    if fach:
        # Delete related stundenplan entries first
        db_write("DELETE FROM stundenplan WHERE fach_id=%s", (fach_id,))
        # Delete the fach
        db_write("DELETE FROM faecher WHERE id=%s", (fach_id,))
    
    return redirect(url_for("teacher_week"))


# -----------------------------
# LEHRER FACH BEARBEITEN
# -----------------------------
@app.route("/lesson/edit/<int:fach_id>", methods=["GET", "POST"])
@login_required
def edit_lesson(fach_id):
    if current_user.role != 'teacher':
        return redirect(url_for("week_view"))
    
    # Get lehrer_id for current user
    lehrer = db_read("SELECT id FROM lehrer WHERE user_id=%s", (current_user.id,), single=True)
    if not lehrer:
        return redirect(url_for("teacher_week"))
    
    # Ensure the lesson belongs to the current teacher
    fach = db_read(
        "SELECT * FROM faecher WHERE id=%s AND lehrer_id=%s",
        (fach_id, lehrer["id"]),
        single=True
    )
    if not fach:
        return redirect(url_for("teacher_week"))
    
    if request.method == "POST":
        subject = request.form["subject"]
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
        
        # Check for time conflicts - teacher can't have multiple classes at the same time
        conflict = db_read("""
            SELECT id FROM faecher 
            WHERE lehrer_id=%s AND tag=%s AND startzeit=%s AND endzeit=%s AND id != %s
        """, (lehrer["id"], tag, start, end, fach_id), single=True)
        
        if conflict:
            # Teacher already has a class at this time
            raum = db_read("SELECT raumnummer FROM raum WHERE id=%s", (fach["raum_id"],), single=True)
            fach_data = {
                "fachname": fach["fachname"],
                "raumnummer": raum["raumnummer"] if raum else "unbekannt",
                "weekday": tag_to_number.get(fach["tag"], "1"),
                "startzeit": str(fach["startzeit"])[:5],
                "endzeit": str(fach["endzeit"])[:5]
            }
            return render_template("edit_lesson.html", fach=fach_data, error="Du hast bereits ein Fach zu dieser Zeit!")
        
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
        
        # Update the fach
        db_write(
            "UPDATE faecher SET fachname=%s, raum_id=%s, tag=%s, startzeit=%s, endzeit=%s WHERE id=%s",
            (subject, raum["id"], tag, start, end, fach_id)
        )
        
        return redirect(url_for("teacher_week"))
    
    # Convert tag back to number for form
    tag_to_number = {
        "Montag": "1",
        "Dienstag": "2",
        "Mittwoch": "3",
        "Donnerstag": "4",
        "Freitag": "5"
    }
    
    # Get raum info
    raum = db_read("SELECT raumnummer FROM raum WHERE id=%s", (fach["raum_id"],), single=True)
    
    fach_data = {
        "fachname": fach["fachname"],
        "raumnummer": raum["raumnummer"] if raum else "unbekannt",
        "weekday": tag_to_number.get(fach["tag"], "1"),
        "startzeit": str(fach["startzeit"])[:5],
        "endzeit": str(fach["endzeit"])[:5]
    }
    
    return render_template("edit_lesson.html", fach=fach_data)


# -----------------------------
# PLUSPUNKTE CALCULATOR
# -----------------------------
@app.route("/pluspunkte")
@login_required
def pluspunkte():
    if current_user.role != 'student':
        return redirect(url_for("teacher_week"))
    
    # Get all unique subjects from the student's schedule
    subjects = db_read("""
        SELECT DISTINCT faecher.fachname
        FROM stundenplan
        JOIN faecher ON stundenplan.fach_id = faecher.id
        WHERE stundenplan.user_id = %s
        ORDER BY faecher.fachname
    """, (current_user.id,)) or []
    
    # Load saved data
    saved_data = {}
    try:
        for subject in subjects:
            fachname = subject['fachname']
            
            # Get Fach-Gewichtung
            gewichtung = db_read(
                "SELECT gewichtung FROM fach_gewichtungen WHERE user_id=%s AND fachname=%s",
                (current_user.id, fachname),
                single=True
            )
            
            # Get all Prüfungen for this subject
            pruefungen = db_read(
                "SELECT id, note, gewichtung FROM pruefungen WHERE user_id=%s AND fachname=%s ORDER BY id",
                (current_user.id, fachname)
            ) or []
            
            saved_data[fachname] = {
                'fach_gewichtung': float(gewichtung['gewichtung']) if gewichtung else 1.0,
                'pruefungen': [{'note': float(p['note']), 'gewichtung': float(p['gewichtung'])} for p in pruefungen]
            }
    except Exception as e:
        logging.error(f"Error loading pluspunkte data: {e}")
        for subject in subjects:
            saved_data[subject['fachname']] = {
                'fach_gewichtung': 1.0,
                'pruefungen': []
            }
    
    return render_template("pluspunkte.html", subjects=subjects, saved_data=saved_data)


# -----------------------------
# PLUSPUNKTE SPEICHERN
# -----------------------------
@app.route("/pluspunkte/save", methods=["POST"])
@login_required
def save_pluspunkte():
    if current_user.role != 'student':
        print("ERROR: User is not a student")
        return {'success': False, 'error': 'Unauthorized'}, 403
    
    try:
        import json
        data = json.loads(request.data)
        
        fachname = data.get('fachname')
        fach_gewichtung = data.get('fach_gewichtung', 1.0)
        pruefungen = data.get('pruefungen', [])
        
        print(f"\n=== SAVE PLUSPUNKTE DEBUG ===")
        print(f"User ID: {current_user.id}")
        print(f"Fachname: {fachname}")
        print(f"Fach-Gewichtung: {fach_gewichtung}")
        print(f"Prüfungen: {pruefungen}")
        
        # Save or update Fach-Gewichtung
        existing = db_read(
            "SELECT id FROM fach_gewichtungen WHERE user_id=%s AND fachname=%s",
            (current_user.id, fachname),
            single=True
        )
        
        if existing:
            print(f"Updating existing fach_gewichtung ID: {existing['id']}")
            db_write(
                "UPDATE fach_gewichtungen SET gewichtung=%s WHERE id=%s",
                (fach_gewichtung, existing['id'])
            )
        else:
            print("Inserting new fach_gewichtung")
            db_write(
                "INSERT INTO fach_gewichtungen (user_id, fachname, gewichtung) VALUES (%s, %s, %s)",
                (current_user.id, fachname, fach_gewichtung)
            )
        
        # Delete old Prüfungen for this subject
        print(f"Deleting old pruefungen for {fachname}")
        db_write("DELETE FROM pruefungen WHERE user_id=%s AND fachname=%s", (current_user.id, fachname))
        
        # Insert new Prüfungen
        print(f"Inserting {len(pruefungen)} new pruefungen")
        for i, pruefung in enumerate(pruefungen):
            print(f"  Prüfung {i+1}: Note={pruefung['note']}, Gewichtung={pruefung['gewichtung']}")
            db_write(
                "INSERT INTO pruefungen (user_id, fachname, note, gewichtung) VALUES (%s, %s, %s, %s)",
                (current_user.id, fachname, pruefung['note'], pruefung['gewichtung'])
            )
        
        print("Save successful!")
        return {'success': True}
    except Exception as e:
        print(f"ERROR saving pluspunkte: {e}")
        import traceback
        print(traceback.format_exc())
        logging.error(f"Error saving pluspunkte: {e}")
        return {'success': False, 'error': str(e)}, 500


# -----------------------------
# TO-DO LISTE
# -----------------------------
@app.route("/todos")
@login_required
def todos():
    from datetime import date
    
    try:
        # Get all todos for current user, sorted by: uncompleted first, then by due date
        all_todos = db_read("""
            SELECT id, title, completed, due_date, created_at
            FROM todos
            WHERE user_id = %s
            ORDER BY completed ASC, due_date ASC, created_at DESC
        """, (current_user.id,)) or []
    except Exception as e:
        logging.error(f"Error loading todos: {e}")
        all_todos = []
    
    today = date.today()
    
    return render_template("todos.html", todos=all_todos, today=today)


@app.route("/todos/add", methods=["POST"])
@login_required
def add_todo():
    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", None)
    
    print(f"\n=== ADD TODO DEBUG ===")
    print(f"User ID: {current_user.id}")
    print(f"Title: {title}")
    print(f"Due date (raw): {request.form.get('due_date')}")
    print(f"Due date (processed): {due_date}")
    
    if not title:
        print("ERROR: No title provided")
        return redirect(url_for("todos"))
    
    # Convert empty string to None for SQL
    if due_date == "":
        due_date = None
    
    try:
        print(f"Attempting INSERT with user_id={current_user.id}, title='{title}', due_date={due_date}")
        db_write(
            "INSERT INTO todos (user_id, title, due_date) VALUES (%s, %s, %s)",
            (current_user.id, title, due_date)
        )
        print("INSERT successful!")
    except Exception as e:
        print(f"ERROR in db_write: {e}")
        import traceback
        print(traceback.format_exc())
        logging.error(f"Error adding todo: {e}")
    
    return redirect(url_for("todos"))


@app.route("/todos/toggle/<int:todo_id>", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    try:
        # Verify todo belongs to current user
        todo = db_read(
            "SELECT id, completed FROM todos WHERE id=%s AND user_id=%s",
            (todo_id, current_user.id),
            single=True
        )
        
        if todo:
            new_status = not todo["completed"]
            db_write(
                "UPDATE todos SET completed=%s WHERE id=%s",
                (new_status, todo_id)
            )
    except Exception as e:
        logging.error(f"Error toggling todo: {e}")
    
    return redirect(url_for("todos"))


@app.route("/todos/delete/<int:todo_id>", methods=["POST"])
@login_required
def delete_todo(todo_id):
    try:
        # Verify todo belongs to current user
        db_write(
            "DELETE FROM todos WHERE id=%s AND user_id=%s",
            (todo_id, current_user.id)
        )
    except Exception as e:
        logging.error(f"Error deleting todo: {e}")
    
    return redirect(url_for("todos"))


# -----------------------------
# START APP
# -----------------------------
if __name__ == "__main__":
    app.run()
