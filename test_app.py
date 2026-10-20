import pytest
from app import app, tasks


@pytest.fixture
def client():
    app.config["TESTING"] = True
    tasks.clear()
    with app.test_client() as c:
        yield c


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_add_task(client):
    response = client.post("/add", data={"title": "Buy milk"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Buy milk" in response.data


def test_delete_task(client):
    client.post("/add", data={"title": "Temp task"})
    task_id = tasks[0]["id"]
    client.post(f"/delete/{task_id}")
    assert len(tasks) == 0


def test_api_tasks(client):
    client.post("/add", data={"title": "API task"})
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.get_json()[0]["title"] == "API task"


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def test_deliberate_fail():
    assert 1 == 2
