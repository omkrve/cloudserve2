import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask, abort, flash, g, jsonify, redirect,
    render_template, request, send_from_directory,
    session, url_for
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("CLOUDSERVE_DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = Path(os.environ.get("CLOUDSERVE_UPLOAD_DIR", BASE_DIR / "uploads"))
DATABASE = DATA_DIR / "cloudserve.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 MB per request
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
)

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "Set SECRET_KEY as an environment variable before starting CloudServe."
    )

csrf = CSRFProtect(app)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".txt", ".log"}
ALLOWED_STATUSES = {"Open", "In Progress", "Resolved", "Closed"}
ALLOWED_PRIORITIES = {"Low", "Medium", "High", "Critical"}
ALLOWED_CATEGORIES = {
    "Hardware", "Software", "Network", "Account Access", "Other"
}


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
                CHECK(role IN ('user', 'admin')),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Open',
            user_id INTEGER NOT NULL,
            attachment_name TEXT,
            attachment_disk_name TEXT,
            assigned_to INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(assigned_to) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ticket_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
            FOREIGN KEY(actor_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_tickets_user
            ON tickets(user_id);
        CREATE INDEX IF NOT EXISTS idx_tickets_status
            ON tickets(status);
        CREATE INDEX IF NOT EXISTS idx_history_ticket
            ON ticket_history(ticket_id);
    """)

    # Bootstrap an admin only when credentials are explicitly supplied.
    admin_username = os.environ.get("ADMIN_USERNAME", "").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()

    if admin_username and admin_password and admin_email:
        existing = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (admin_username, admin_email)
        ).fetchone()

        if not existing:
            db.execute(
                """INSERT OR IGNORE INTO users
                   (username, email, password_hash, role, created_at)
                   VALUES (?, ?, ?, 'admin', ?)""",
                (
                    admin_username,
                    admin_email,
                    generate_password_hash(admin_password),
                    now_utc()
                )
            )

    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"current_user": g.get("current_user")}


@app.before_request
def load_current_user():
    g.current_user = None
    user_id = session.get("user_id")
    if user_id:
        g.current_user = get_db().execute(
            "SELECT id, username, email, role FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def validate_attachment(file_storage):
    """Allow only known extensions and matching basic file signatures."""
    if not file_storage or not file_storage.filename:
        return None, None, None

    original = secure_filename(file_storage.filename)
    if not original or not allowed_file(original):
        return None, None, "Use a PNG, JPG, JPEG, PDF, TXT or LOG file."

    data = file_storage.stream.read(32)
    file_storage.stream.seek(0)
    extension = Path(original).suffix.lower()

    if extension == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None, None, "The file does not appear to be a valid PNG."
    if extension in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8\xff"):
        return None, None, "The file does not appear to be a valid JPEG."
    if extension == ".pdf" and not data.startswith(b"%PDF-"):
        return None, None, "The file does not appear to be a valid PDF."
    if extension in {".txt", ".log"}:
        content = file_storage.stream.read(1024 * 1024)
        file_storage.stream.seek(0)
        if b"\x00" in content:
            return None, None, "Text and log files cannot contain binary data."

    disk_name = f"{uuid.uuid4().hex}{extension}"
    return original, disk_name, None


def save_attachment(file_storage):
    original, disk_name, error = validate_attachment(file_storage)
    if error:
        return None, None, error
    if not disk_name:
        return None, None, None

    destination = UPLOAD_DIR / disk_name
    file_storage.save(destination)
    return original, disk_name, None


def record_history(db, ticket_id, action, old_value=None, new_value=None):
    db.execute(
        """INSERT INTO ticket_history
           (ticket_id, actor_id, action, old_value, new_value, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            ticket_id, session["user_id"], action,
            old_value, new_value, now_utc()
        )
    )


@app.get("/health")
def health():
    return jsonify({"service": "cloudserve", "status": "healthy"})


@app.get("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username):
            flash("Username must be 3–30 characters using letters, numbers, dots, underscores or hyphens.", "danger")
        elif len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid email address.", "danger")
        elif len(password) < 10 or len(password) > 128:
            flash("Password must be between 10 and 128 characters.", "danger")
        else:
            db = get_db()
            try:
                db.execute(
                    """INSERT INTO users
                       (username, email, password_hash, role, created_at)
                       VALUES (?, ?, ?, 'user', ?)""",
                    (username, email, generate_password_hash(password), now_utc())
                )
                db.commit()
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username or email is already registered.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (identity, identity.lower())
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username/email or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    db = get_db()
    is_admin = session.get("role") == "admin"

    if is_admin:
        tickets = db.execute(
            """SELECT t.*, u.username AS requester
               FROM tickets t JOIN users u ON u.id = t.user_id
               ORDER BY t.updated_at DESC LIMIT 100"""
        ).fetchall()
        counts = {
            row["status"]: row["count"]
            for row in db.execute(
                "SELECT status, COUNT(*) AS count FROM tickets GROUP BY status"
            ).fetchall()
        }
        total = db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    else:
        tickets = db.execute(
            """SELECT t.*, u.username AS requester
               FROM tickets t JOIN users u ON u.id = t.user_id
               WHERE t.user_id = ? ORDER BY t.updated_at DESC LIMIT 100""",
            (session["user_id"],)
        ).fetchall()
        counts = {
            row["status"]: row["count"]
            for row in db.execute(
                """SELECT status, COUNT(*) AS count FROM tickets
                   WHERE user_id = ? GROUP BY status""",
                (session["user_id"],)
            ).fetchall()
        }
        total = sum(counts.values())

    return render_template(
        "dashboard.html", tickets=tickets, counts=counts,
        total=total, is_admin=is_admin
    )


@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        priority = request.form.get("priority", "Medium")
        file_storage = request.files.get("attachment")

        if not title or len(title) > 120:
            flash("Title is required and must be at most 120 characters.", "danger")
            return render_template("ticket_new.html")
        if len(description) < 10 or len(description) > 10000:
            flash("Description must be between 10 and 10,000 characters.", "danger")
            return render_template("ticket_new.html")
        if category not in ALLOWED_CATEGORIES or priority not in ALLOWED_PRIORITIES:
            flash("Select a valid category and priority.", "danger")
            return render_template("ticket_new.html")

        original, disk_name, error = save_attachment(file_storage)
        if error:
            flash(error, "danger")
            return render_template("ticket_new.html")

        db = get_db()
        timestamp = now_utc()
        cursor = db.execute(
            """INSERT INTO tickets
               (title, description, category, priority, status, user_id,
                attachment_name, attachment_disk_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?)""",
            (
                title, description, category, priority, session["user_id"],
                original, disk_name, timestamp, timestamp
            )
        )
        ticket_id = cursor.lastrowid
        record_history(db, ticket_id, "Ticket created", None, "Open")
        db.commit()
        flash(f"Ticket CS-{ticket_id:04d} created successfully.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    return render_template("ticket_new.html")


@app.get("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    db = get_db()
    ticket = db.execute(
        """SELECT t.*, u.username AS requester,
                  a.username AS assignee
           FROM tickets t
           JOIN users u ON u.id = t.user_id
           LEFT JOIN users a ON a.id = t.assigned_to
           WHERE t.id = ?""",
        (ticket_id,)
    ).fetchone()

    if not ticket:
        abort(404)
    if session.get("role") != "admin" and ticket["user_id"] != session["user_id"]:
        abort(403)

    comments = db.execute(
        """SELECT c.*, u.username, u.role
           FROM comments c JOIN users u ON u.id = c.user_id
           WHERE c.ticket_id = ? ORDER BY c.created_at""",
        (ticket_id,)
    ).fetchall()
    history = db.execute(
        """SELECT h.*, u.username FROM ticket_history h
           JOIN users u ON u.id = h.actor_id
           WHERE h.ticket_id = ? ORDER BY h.created_at DESC""",
        (ticket_id,)
    ).fetchall()
    agents = db.execute(
        "SELECT id, username FROM users WHERE role = 'admin' ORDER BY username"
    ).fetchall()

    return render_template(
        "ticket_detail.html", ticket=ticket, comments=comments,
        history=history, agents=agents,
        statuses=sorted(ALLOWED_STATUSES),
        priorities=sorted(ALLOWED_PRIORITIES)
    )


@app.post("/tickets/<int:ticket_id>/comment")
@login_required
def add_comment(ticket_id):
    db = get_db()
    ticket = db.execute(
        "SELECT id, user_id FROM tickets WHERE id = ?", (ticket_id,)
    ).fetchone()
    if not ticket:
        abort(404)
    if session.get("role") != "admin" and ticket["user_id"] != session["user_id"]:
        abort(403)

    body = request.form.get("body", "").strip()
    if not body or len(body) > 3000:
        flash("Comment must contain 1–3,000 characters.", "danger")
    else:
        db.execute(
            """INSERT INTO comments (ticket_id, user_id, body, created_at)
               VALUES (?, ?, ?, ?)""",
            (ticket_id, session["user_id"], body, now_utc())
        )
        db.execute(
            "UPDATE tickets SET updated_at = ? WHERE id = ?",
            (now_utc(), ticket_id)
        )
        record_history(db, ticket_id, "Comment added")
        db.commit()
        flash("Comment added.", "success")

    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.post("/tickets/<int:ticket_id>/manage")
@admin_required
def manage_ticket(ticket_id):
    db = get_db()
    ticket = db.execute(
        "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
    ).fetchone()
    if not ticket:
        abort(404)

    status = request.form.get("status", ticket["status"])
    priority = request.form.get("priority", ticket["priority"])
    assignee_raw = request.form.get("assigned_to", "")

    if status not in ALLOWED_STATUSES or priority not in ALLOWED_PRIORITIES:
        flash("Invalid status or priority.", "danger")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    assignee = None
    if assignee_raw:
        try:
            assignee = int(assignee_raw)
        except ValueError:
            flash("Invalid assignee.", "danger")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))

        valid_assignee = db.execute(
            "SELECT id FROM users WHERE id = ? AND role = 'admin'",
            (assignee,)
        ).fetchone()
        if not valid_assignee:
            flash("Select a valid administrator.", "danger")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    if status != ticket["status"]:
        record_history(db, ticket_id, "Status changed", ticket["status"], status)
    if priority != ticket["priority"]:
        record_history(db, ticket_id, "Priority changed", ticket["priority"], priority)
    if assignee != ticket["assigned_to"]:
        record_history(
            db, ticket_id, "Assignee changed",
            str(ticket["assigned_to"] or ""), str(assignee or "")
        )

    db.execute(
        """UPDATE tickets SET status = ?, priority = ?, assigned_to = ?,
           updated_at = ? WHERE id = ?""",
        (status, priority, assignee, now_utc(), ticket_id)
    )
    db.commit()
    flash("Ticket updated.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.get("/tickets/<int:ticket_id>/attachment")
@login_required
def download_attachment(ticket_id):
    ticket = get_db().execute(
        """SELECT user_id, attachment_disk_name, attachment_name
           FROM tickets WHERE id = ?""",
        (ticket_id,)
    ).fetchone()
    if not ticket:
        abort(404)
    if session.get("role") != "admin" and ticket["user_id"] != session["user_id"]:
        abort(403)
    if not ticket["attachment_disk_name"]:
        abort(404)

    return send_from_directory(
        UPLOAD_DIR,
        ticket["attachment_disk_name"],
        as_attachment=True,
        download_name=ticket["attachment_name"],
        max_age=0
    )


@app.errorhandler(403)
def forbidden(_error):
    return render_template(
        "error.html", code=403,
        message="You do not have permission to access this resource."
    ), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html", code=404,
        message="The requested page or ticket could not be found."
    ), 404


@app.errorhandler(413)
def too_large(_error):
    return render_template(
        "error.html", code=413,
        message="The upload is too large. The maximum request size is 5 MB."
    ), 413


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)