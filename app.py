import os
import sqlite3
from datetime import date

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from prometheus_client import Gauge
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Exposes /metrics automatically for Prometheus
metrics = PrometheusMetrics(app)
metrics.info("app_info", "Agile Task Tracker info", version="2.0.0")

DB_PATH = os.environ.get("DB_PATH", "tasks.db")
STATUSES = ["To Do", "In Progress", "Done"]
PRIORITIES = ["Low", "Medium", "High"]

# Custom business metrics (these show up in Prometheus and Grafana)
TASKS_GAUGE = Gauge("tracker_tasks", "Number of tasks by status", ["status"])
OVERDUE_GAUGE = Gauge("tracker_tasks_overdue", "Number of overdue tasks")


# ---------- database helpers ----------
def query(sql, args=(), commit=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, args)
        if commit:
            conn.commit()
        return cur.fetchall()
    finally:
        conn.close()


def init_db():
    query(
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'To Do',
            due_date TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""",
        commit=True,
    )
    refresh_metrics()


def load_tasks():
    rows = query(
        """SELECT * FROM tasks ORDER BY
           CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,
           due_date = '', due_date, id"""
    )
    today = date.today().isoformat()
    tasks = []
    for row in rows:
        task = dict(row)
        task["overdue"] = (
            bool(task["due_date"]) and task["due_date"] < today and task["status"] != "Done"
        )
        tasks.append(task)
    return tasks


def get_stats(tasks):
    total = len(tasks)
    counts = {s: sum(1 for t in tasks if t["status"] == s) for s in STATUSES}
    overdue = sum(1 for t in tasks if t["overdue"])
    percent = round(100 * counts["Done"] / total) if total else 0
    return {"total": total, "counts": counts, "overdue": overdue, "percent_done": percent}


def update_gauges(stats):
    for status in STATUSES:
        TASKS_GAUGE.labels(status=status).set(stats["counts"][status])
    OVERDUE_GAUGE.set(stats["overdue"])


def refresh_metrics():
    update_gauges(get_stats(load_tasks()))


def clean_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        return ""


# ---------- web pages ----------
@app.route("/")
def index():
    priority = request.args.get("priority", "")
    q = request.args.get("q", "").strip().lower()

    all_tasks = load_tasks()
    stats = get_stats(all_tasks)
    update_gauges(stats)

    visible = [
        t
        for t in all_tasks
        if (not priority or t["priority"] == priority)
        and (not q or q in t["title"].lower() or q in t["description"].lower())
    ]
    board = {s: [t for t in visible if t["status"] == s] for s in STATUSES}
    return render_template(
        "index.html",
        board=board,
        stats=stats,
        statuses=STATUSES,
        priorities=PRIORITIES,
        selected_priority=priority,
        q=q,
    )


@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    if title:
        priority = request.form.get("priority", "Medium")
        if priority not in PRIORITIES:
            priority = "Medium"
        query(
            "INSERT INTO tasks (title, description, priority, status, due_date) "
            "VALUES (?, ?, ?, 'To Do', ?)",
            (
                title,
                request.form.get("description", "").strip(),
                priority,
                clean_date(request.form.get("due_date", "")),
            ),
            commit=True,
        )
        refresh_metrics()
    return redirect(url_for("index"))


@app.route("/move/<int:task_id>/<status>", methods=["POST"])
def move_task(task_id, status):
    if status not in STATUSES:
        abort(400)
    query("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id), commit=True)
    refresh_metrics()
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    query("DELETE FROM tasks WHERE id = ?", (task_id,), commit=True)
    refresh_metrics()
    return redirect(url_for("index"))


# ---------- API ----------
@app.route("/api/tasks")
def api_tasks():
    return jsonify(load_tasks())


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats(load_tasks()))


@app.route("/health")
def health():
    return jsonify(status="ok")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
