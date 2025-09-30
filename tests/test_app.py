from flask import Flask, request
import pytest
import sqlite3

@pytest.fixture
def client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = ":memory:"

    with app.test_client() as client:
        with app.app_context():
            db = get_db()
            db.execute("CREATE TABLE queue (id INTEGER PRIMARY KEY, name TEXT, group_size INTEGER, status TEXT)")
            db.commit()
        yield client

def get_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    return db

def test_join_page(client):
    response = client.get('/join')
    assert response.status_code == 200
    assert b'Enter your group size' in response.data

def test_join_queue(client):
    response = client.post('/join', data={'name': 'Test Group', 'group_size': 4})
    assert response.data == b"You're in the queue! ✅"

def test_admin_page(client):
    response = client.get('/admin')
    assert response.status_code == 200

def test_reset_queue(client):
    client.post('/join', data={'name': 'Test Group', 'group_size': 4})
    response = client.get('/admin/reset')
    assert response.status_code == 302  # Redirect to admin page
    response = client.get('/admin')
    assert b'0' in response.data  # Assuming it shows the number of groups in queue

def test_next_group(client):
    client.post('/join', data={'name': 'Test Group', 'group_size': 4})
    response = client.get('/admin/next/1')
    assert response.status_code == 302  # Redirect to admin page
    response = client.get('/admin')
    assert b'active' in response.data  # Check if the group is marked as active