import pytest

import app as tracker


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", str(tmp_path / "test.db"))
    tracker.init_db()
    tracker.app.config["TESTING"] = True
    with tracker.app.test_client() as c:
        yield c


def add(client, title="Write report", priority="High", due="2099-01-01", desc="demo"):
    return client.post(
        "/add",
        data={"title": title, "priority": priority, "due_date": due, "description": desc},
        follow_redirects=True,
    )


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Agile Task Tracker" in response.data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_add_task(client):
    response = add(client)
    assert response.status_code == 200
    assert b"Write report" in response.data


def test_empty_title_is_ignored(client):
    add(client, title="   ")
    assert client.get("/api/tasks").get_json() == []


def test_move_task_changes_status(client):
    add(client)
    client.post("/move/1/In%20Progress")
    assert client.get("/api/tasks").get_json()[0]["status"] == "In Progress"


def test_invalid_status_rejected(client):
    add(client)
    assert client.post("/move/1/Nonsense").status_code == 400


def test_delete_task(client):
    add(client)
    client.post("/delete/1")
    assert client.get("/api/tasks").get_json() == []


def test_stats_progress(client):
    add(client, title="A")
    add(client, title="B")
    client.post("/move/1/Done")
    stats = client.get("/api/stats").get_json()
    assert stats["total"] == 2
    assert stats["counts"]["Done"] == 1
    assert stats["percent_done"] == 50


def test_overdue_detection(client):
    add(client, due="2000-01-01")
    assert client.get("/api/stats").get_json()["overdue"] == 1
    client.post("/move/1/Done")
    assert client.get("/api/stats").get_json()["overdue"] == 0


def test_priority_filter(client):
    add(client, title="Urgent thing", priority="High")
    add(client, title="Relaxed thing", priority="Low")
    page = client.get("/?priority=High").data
    assert b"Urgent thing" in page
    assert b"Relaxed thing" not in page


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"tracker_tasks" in response.data
