
import os
import re
import sqlite3
from datetime import date, datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

app = Flask(__name__)
app.config["SECRET_KEY"] = (
    os.environ.get("SECRET_KEY")
    or os.environ.get("FINORA_SECRET_KEY")
    or "dev-only-change-this-key"
)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "finora.db"))
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CATEGORIES = [
    "Food", "Shopping", "Transport", "Entertainment",
    "Bills", "Education", "Health", "Travel", "Salary",
    "Freelance", "Other"
]


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income','expense')),
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                date TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                month TEXT NOT NULL,
                UNIQUE(user_id, category, month),
                FOREIGN KEY(user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target REAL NOT NULL CHECK(target > 0),
                saved REAL NOT NULL DEFAULT 0 CHECK(saved >= 0),
                deadline TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            );
        """)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def categorize(description):
    text = description.lower()
    rules = {
        "Food": ["restaurant", "food", "cafe", "swiggy",
                 "zomato", "grocery"],
        "Transport": ["uber", "ola", "petrol", "metro", "bus"],
        "Shopping": ["amazon", "flipkart", "shopping", "mall"],
        "Bills": ["electricity", "water bill", "recharge", "internet"],
        "Entertainment": ["movie", "netflix", "spotify"],
        "Health": ["hospital", "pharmacy", "medical"],
        "Education": ["college", "course", "book", "tuition"],
        "Travel": ["flight", "hotel", "train", "booking"],
        "Salary": ["salary", "payroll"],
        "Freelance": ["freelance", "client payment"]
    }
    for category, keywords in rules.items():
        if any(word in text for word in keywords):
            return category
    return "Other"


def summary_data(user_id):
    month = date.today().strftime("%Y-%m")
    with get_db() as db:
        income = db.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE user_id=? AND type='income' AND substr(date,1,7)=?
        """, (user_id, month)).fetchone()["total"]

        expenses = db.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE user_id=? AND type='expense' AND substr(date,1,7)=?
        """, (user_id, month)).fetchone()["total"]

        all_income = db.execute("""
            SELECT COALESCE(SUM(amount),0) AS total
            FROM transactions WHERE user_id=? AND type='income'
        """, (user_id,)).fetchone()["total"]

        all_expenses = db.execute("""
            SELECT COALESCE(SUM(amount),0) AS total
            FROM transactions WHERE user_id=? AND type='expense'
        """, (user_id,)).fetchone()["total"]

    savings_rate = (
        max(0, (income - expenses) / income * 100) if income else 0
    )
    score = round(min(100, max(0,
        savings_rate * 0.6 +
        (40 if expenses <= income else 0)
    )))

    return {
        "income": income,
        "expenses": expenses,
        "balance": all_income - all_expenses,
        "savings_rate": round(savings_rate, 1),
        "health_score": score
    }


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="signup")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please complete all fields.", "danger")
            return render_template("auth.html", mode="signup")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("auth.html", mode="signup")

        try:
            with get_db() as db:
                db.execute("""
                    INSERT INTO users(name,email,password_hash)
                    VALUES(?,?,?)
                """, (name, email, generate_password_hash(password)))
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")

    return render_template("auth.html", mode="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE email=?", (email,)
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "danger")

    return render_template("auth.html", mode="login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    summary = summary_data(user_id)

    with get_db() as db:
        recent = db.execute("""
            SELECT * FROM transactions WHERE user_id=?
            ORDER BY date DESC, id DESC LIMIT 5
        """, (user_id,)).fetchall()

        categories = db.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE user_id=? AND type='expense'
              AND substr(date,1,7)=?
            GROUP BY category ORDER BY total DESC
        """, (user_id, date.today().strftime("%Y-%m"))).fetchall()

        goals = db.execute("""
            SELECT * FROM savings_goals
            WHERE user_id=? ORDER BY id DESC LIMIT 3
        """, (user_id,)).fetchall()

    insights = []
    if summary["income"] == 0 and summary["expenses"] == 0:
        insights.append("Add your first transactions to unlock insights.")
    elif summary["expenses"] > summary["income"]:
        insights.append("Your expenses exceed your income this month.")
    else:
        insights.append("Review your savings rate and keep your budget on track.")

    if summary["savings_rate"] >= 20:
        insights.append("Your current savings rate is at least 20%.")

    return render_template(
        "dashboard.html", summary=summary, recent=recent,
        categories=categories, goals=goals, insights=insights
    )


@app.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    user_id = session["user_id"]

    if request.method == "POST":
        kind = request.form.get("type")
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Other")
        raw_amount = request.form.get("amount", "")
        transaction_date = request.form.get("date", "")

        try:
            amount = float(raw_amount)
            parsed_date = datetime.strptime(transaction_date, "%Y-%m-%d")
            if amount <= 0 or kind not in ("income", "expense"):
                raise ValueError()
            if category not in CATEGORIES:
                category = categorize(description)
        except (ValueError, TypeError):
            flash("Enter a valid amount, type and date.", "danger")
            return redirect(url_for("transactions"))

        with get_db() as db:
            db.execute("""
                INSERT INTO transactions
                (user_id,type,amount,category,description,date)
                VALUES(?,?,?,?,?,?)
            """, (user_id, kind, amount, category, description,
                  parsed_date.strftime("%Y-%m-%d")))

        flash("Transaction added successfully.", "success")
        return redirect(url_for("transactions"))

    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM transactions WHERE user_id=?
            ORDER BY date DESC, id DESC
        """, (user_id,)).fetchall()

    return render_template(
        "transactions.html", transactions=rows,
        categories=CATEGORIES, today=date.today().isoformat()
    )


@app.route("/transactions/delete/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    with get_db() as db:
        db.execute("""
            DELETE FROM transactions WHERE id=? AND user_id=?
        """, (transaction_id, session["user_id"]))
    flash("Transaction deleted.", "success")
    return redirect(request.referrer or url_for("transactions"))


@app.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():
    user_id = session["user_id"]
    month = date.today().strftime("%Y-%m")

    if request.method == "POST":
        category = request.form.get("category", "")
        try:
            amount = float(request.form.get("amount", ""))
            if amount <= 0 or category not in CATEGORIES:
                raise ValueError()
        except ValueError:
            flash("Enter a valid budget and category.", "danger")
            return redirect(url_for("budgets"))

        with get_db() as db:
            db.execute("""
                INSERT INTO budgets(user_id,category,amount,month)
                VALUES(?,?,?,?)
                ON CONFLICT(user_id,category,month)
                DO UPDATE SET amount=excluded.amount
            """, (user_id, category, amount, month))

        flash("Budget saved.", "success")
        return redirect(url_for("budgets"))

    with get_db() as db:
        rows = db.execute("""
            SELECT b.*,
                COALESCE((
                    SELECT SUM(t.amount) FROM transactions t
                    WHERE t.user_id=b.user_id
                      AND t.category=b.category
                      AND t.type='expense'
                      AND substr(t.date,1,7)=b.month
                ),0) AS spent
            FROM budgets b
            WHERE b.user_id=? AND b.month=?
        """, (user_id, month)).fetchall()

    return render_template("budgets.html", budgets=rows,
                           categories=CATEGORIES, month=month)


@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        deadline = request.form.get("deadline") or None
        try:
            target = float(request.form.get("target", ""))
            saved = float(request.form.get("saved", "0") or 0)
            if not name or target <= 0 or saved < 0:
                raise ValueError()
            if deadline:
                datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            flash("Enter valid savings goal details.", "danger")
            return redirect(url_for("goals"))

        with get_db() as db:
            db.execute("""
                INSERT INTO savings_goals
                (user_id,name,target,saved,deadline)
                VALUES(?,?,?,?,?)
            """, (user_id, name, target, saved, deadline))
        flash("Savings goal created.", "success")
        return redirect(url_for("goals"))

    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM savings_goals
            WHERE user_id=? ORDER BY id DESC
        """, (user_id,)).fetchall()

    return render_template("goals.html", goals=rows)


@app.route("/goals/update/<int:goal_id>", methods=["POST"])
@login_required
def update_goal(goal_id):
    try:
        saved = float(request.form.get("saved", ""))
        if saved < 0:
            raise ValueError()
    except ValueError:
        flash("Enter a valid saved amount.", "danger")
        return redirect(url_for("goals"))

    with get_db() as db:
        db.execute("""
            UPDATE savings_goals SET saved=?
            WHERE id=? AND user_id=?
        """, (saved, goal_id, session["user_id"]))

    return redirect(url_for("goals"))


@app.route("/analytics")
@login_required
def analytics():
    user_id = session["user_id"]

    with get_db() as db:
        rows = db.execute("""
            SELECT substr(date,1,7) AS month, type,
                   SUM(amount) AS total
            FROM transactions WHERE user_id=?
            GROUP BY substr(date,1,7), type ORDER BY month
        """, (user_id,)).fetchall()

        categories = db.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE user_id=? AND type='expense'
            GROUP BY category ORDER BY total DESC
        """, (user_id,)).fetchall()

    monthly = {}
    for row in rows:
        monthly.setdefault(row["month"], {"income": 0, "expense": 0})
        monthly[row["month"]][row["type"]] = row["total"]

    return render_template(
        "analytics.html",
        months=list(monthly.keys()),
        incomes=[monthly[m]["income"] for m in monthly],
        expenses=[monthly[m]["expense"] for m in monthly],
        categories=[r["category"] for r in categories],
        category_totals=[r["total"] for r in categories]
    )


@app.route("/api/summary")
@login_required
def api_summary():
    return jsonify(summary_data(session["user_id"]))


@app.route("/pdf-analyzer", methods=["GET", "POST"])
@login_required
def pdf_analyzer():
    preview = []

    if request.method == "POST":
        file = request.files.get("statement")
        if not file or not file.filename:
            flash("Choose a PDF statement first.", "danger")
            return redirect(url_for("pdf_analyzer"))

        if not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are accepted.", "danger")
            return redirect(url_for("pdf_analyzer"))

        try:
            reader = PdfReader(BytesIO(file.read()))
            if reader.is_encrypted:
                flash("Please upload an unlocked PDF.", "danger")
                return redirect(url_for("pdf_analyzer"))

            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                flash("No readable text found. Scanned PDFs need OCR.", "danger")
                return redirect(url_for("pdf_analyzer"))

            # General example parser. Bank statement formats vary.
            for line in text.splitlines():
                amount_match = re.search(r"(-?\d[\d,]*\.\d{2})", line)
                date_match = re.search(
                    r"\b(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})\b",
                    line
                )
                if not amount_match or not date_match:
                    continue

                try:
                    raw_date = date_match.group(1)
                    parsed_date = None
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y",
                                "%d-%m-%Y", "%m/%d/%Y"):
                        try:
                            parsed_date = datetime.strptime(raw_date, fmt)
                            break
                        except ValueError:
                            continue
                    if not parsed_date:
                        continue

                    amount = abs(float(amount_match.group(1).replace(",", "")))
                    description = line.replace(raw_date, "").strip()
                    description = description.replace(amount_match.group(1), "").strip()
                    low = line.lower()
                    kind = "income" if any(
                        word in low for word in ("credit", "deposit", "salary")
                    ) else "expense"

                    preview.append({
                        "date": parsed_date.strftime("%Y-%m-%d"),
                        "description": description[:150],
                        "amount": amount,
                        "type": kind,
                        "category": categorize(description)
                    })
                except (ValueError, TypeError):
                    continue

            session["pdf_preview"] = preview[:500]
            flash(
                f"Found {len(preview)} possible rows. Review before importing.",
                "success" if preview else "warning"
            )

        except Exception:
            app.logger.exception("PDF parsing failed")
            flash("Unable to read this PDF statement.", "danger")

    return render_template(
        "pdf_analyzer.html", preview=session.get("pdf_preview", [])
    )


@app.route("/pdf-analyzer/import", methods=["POST"])
@login_required
def import_pdf_transactions():
    preview = session.get("pdf_preview", [])
    if not preview:
        flash("Upload and review a statement first.", "warning")
        return redirect(url_for("pdf_analyzer"))

    with get_db() as db:
        for item in preview:
            db.execute("""
                INSERT INTO transactions
                (user_id,type,amount,category,description,date)
                VALUES(?,?,?,?,?,?)
            """, (
                session["user_id"], item["type"], item["amount"],
                item["category"], item["description"], item["date"]
            ))

    session.pop("pdf_preview", None)
    flash(f"Imported {len(preview)} transactions.", "success")
    return redirect(url_for("transactions"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("true", "1")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
