from flask import Flask, render_template, request, redirect, url_for, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Exposes /metrics automatically for Prometheus
metrics = PrometheusMetrics(app)
metrics.info("app_info", "To-Do application info", version="1.0.0")

tasks = []  # in-memory storage (no database needed)


@app.route("/")
def index():
    return render_template("index.html", tasks=tasks)


@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    if title:
        new_id = max((t["id"] for t in tasks), default=0) + 1
        tasks.append({"id": new_id, "title": title})
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    tasks[:] = [t for t in tasks if t["id"] != task_id]
    return redirect(url_for("index"))


@app.route("/api/tasks")
def api_tasks():
    return jsonify(tasks)


@app.route("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
